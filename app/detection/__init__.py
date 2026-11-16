"""Detecção de momentos interessantes (Fase 3).

Contrato futuro:
- analisar áudio (energia, picos, fala);
- transcrever com Faster-Whisper;
- opcionalmente ler chat com autorização explícita;
- produzir pontuações e janelas candidatas para o módulo de clipping.

A Fase 1 não executa detecção: apenas ingere gravações completas.
"""
