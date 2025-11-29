import os
import re
import asyncio
from pathlib import Path
from django.core.management.base import BaseCommand
from asgiref.sync import async_to_sync
import tiktoken


class Command(BaseCommand):
    help = 'Indexa los archivos de entrenamiento en la base de datos vectorial'
    
    def __init__(self):
        super().__init__()
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.chunk_size = 500
        self.chunk_overlap = 50
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Elimina todos los chunks existentes antes de indexar',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se indexaría sin hacer cambios',
        )
    
    def handle(self, *args, **options):
        async_to_sync(self._handle_async)(*args, **options)
    
    async def _handle_async(self, *args, **options):
        from chatbot_ai.models import ChatbotKnowledgeChunk
        from chatbot_ai.vector_service import vector_service
        
        training_dir = Path(__file__).parent.parent.parent / 'ai-training'
        
        if not training_dir.exists():
            self.stderr.write(self.style.ERROR(f'Directorio no encontrado: {training_dir}'))
            return
        
        if options['clear'] and not options['dry_run']:
            count = await asyncio.to_thread(ChatbotKnowledgeChunk.objects.all().delete)
            self.stdout.write(self.style.WARNING(f'Eliminados {count[0]} chunks existentes'))
        
        txt_files = list(training_dir.rglob('*.txt'))
        self.stdout.write(f'Encontrados {len(txt_files)} archivos .txt')
        
        if options['dry_run']:
            self._dry_run_report(txt_files, training_dir)
            return
        
        total_chunks = 0
        total_tokens = 0
        
        for file_path in txt_files:
            try:
                course = self._detect_course(file_path, training_dir)
                module = self._extract_module(file_path.name)
                
                content = file_path.read_text(encoding='utf-8')
                chunks = self._split_into_chunks(content)
                
                if not chunks:
                    self.stdout.write(f'  ⚠️ Sin contenido: {file_path.name}')
                    continue
                
                chunk_texts = [c['text'] for c in chunks]
                
                self.stdout.write(f'  📄 {file_path.name}: {len(chunks)} chunks')
                
                batch_size = 20
                for i in range(0, len(chunk_texts), batch_size):
                    batch = chunk_texts[i:i+batch_size]
                    embeddings = await vector_service.create_embeddings_batch(batch)
                    
                    for j, embedding in enumerate(embeddings):
                        chunk_data = chunks[i + j]
                        await asyncio.to_thread(
                            ChatbotKnowledgeChunk.objects.create,
                            content=chunk_data['text'],
                            embedding=embedding,
                            source_file=file_path.name,
                            course=course,
                            module=module,
                            chunk_index=i + j,
                            token_count=chunk_data['tokens']
                        )
                        total_tokens += chunk_data['tokens']
                    
                    total_chunks += len(batch)
                
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'  ❌ Error en {file_path.name}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Indexación completada: {total_chunks} chunks, ~{total_tokens} tokens'
        ))
        
        estimated_cost = (total_tokens / 1_000_000) * 0.02
        self.stdout.write(f'💰 Costo estimado de embeddings: ${estimated_cost:.4f}')
    
    def _detect_course(self, file_path: Path, base_dir: Path) -> str:
        """Detecta el curso basado en la ruta del archivo"""
        relative = file_path.relative_to(base_dir)
        parts = relative.parts
        
        if len(parts) > 0:
            first_dir = parts[0].lower()
            if 'pro' in first_dir:
                return 'imax_pro'
            elif 'launch' in first_dir:
                return 'imax_launch'
        
        return 'imax_launch'
    
    def _extract_module(self, filename: str) -> str:
        """Extrae el módulo del nombre del archivo"""
        name = filename.replace('.txt', '').replace('Copia de ', '')
        
        patterns = [
            r'^(M\s*\d+[\.\d]*)',
            r'^(DI?A\s*\d+)',
            r'^(Fase\s*\d+)',
            r'^(Módulo\s*\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return name[:50] if len(name) > 50 else name
    
    def _split_into_chunks(self, text: str) -> list:
        """Divide el texto en chunks con overlap"""
        text = text.strip()
        if not text:
            return []
        
        tokens = self.tokenizer.encode(text)
        chunks = []
        
        start = 0
        while start < len(tokens):
            end = start + self.chunk_size
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            chunks.append({
                'text': chunk_text.strip(),
                'tokens': len(chunk_tokens)
            })
            
            start = end - self.chunk_overlap
        
        return chunks
    
    def _dry_run_report(self, files: list, base_dir: Path):
        """Muestra reporte de dry-run"""
        total_size = 0
        by_course = {'imax_launch': 0, 'imax_pro': 0}
        
        for f in files:
            size = f.stat().st_size
            total_size += size
            course = self._detect_course(f, base_dir)
            by_course[course] += 1
        
        self.stdout.write(f'\n📊 Reporte Dry-Run:')
        self.stdout.write(f'  - Total archivos: {len(files)}')
        self.stdout.write(f'  - Tamaño total: {total_size / 1024:.2f} KB')
        self.stdout.write(f'  - IMAX Launch: {by_course["imax_launch"]} archivos')
        self.stdout.write(f'  - IMAX Pro: {by_course["imax_pro"]} archivos')
        
        estimated_tokens = int(total_size / 4)
        estimated_chunks = estimated_tokens // self.chunk_size
        estimated_cost = (estimated_tokens / 1_000_000) * 0.02
        
        self.stdout.write(f'\n💡 Estimaciones:')
        self.stdout.write(f'  - Tokens: ~{estimated_tokens:,}')
        self.stdout.write(f'  - Chunks: ~{estimated_chunks:,}')
        self.stdout.write(f'  - Costo embeddings: ~${estimated_cost:.4f}')

