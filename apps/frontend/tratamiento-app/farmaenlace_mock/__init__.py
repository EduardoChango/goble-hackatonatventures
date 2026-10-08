"""Mock de Farmaenlace: simula el sistema de la farmacia para el MVP.

En la realidad es un sistema externo. El contrato (POST /demanda, POST /pedidos y el callback firmado
hacia /api/v1/webhooks/farmaenlace) está pensado para cambiar este mock por la API real sin tocar
el módulo de abastecimiento.
"""
