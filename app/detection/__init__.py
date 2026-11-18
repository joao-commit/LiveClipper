"""Núcleo de detecção de momentos interessantes do LiveClipper 2.0.

Este é o principal módulo funcional planejado. Ele receberá gravações
catalogadas de fontes autorizadas e produzirá candidatos a clipe com tempos
relativos ao início de uma sessão de captura.

Pipeline planejado (ainda não implementado):
- resolver a sessão de captura e a ordem dos segmentos;
- obter metadados e extrair áudio com FFprobe/FFmpeg;
- detectar energia/picos de áudio;
- transcrever com Faster-Whisper;
- combinar evidências em candidatos com início, fim, descrição e score;
- persistir em ``clip_candidates``.

Fora do escopo deste pacote: editar/recortar vídeo, gerar Shorts, converter
para 9:16, adicionar legendas ou publicar em qualquer plataforma. OpenCV não
será usado. Nesta revisão o pacote contém apenas documentação; nenhum
detector, stub executável ou rota é criado.
"""
