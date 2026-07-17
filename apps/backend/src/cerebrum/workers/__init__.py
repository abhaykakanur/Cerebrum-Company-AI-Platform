"""Background Processing Layer: the nine named Workers (Connector, OCR,
Embedding, Entity, Relationship, Search, Analytics, Notification, Cleanup)
and their Task/Workflow definitions.

See docs/architecture/specification/36_Background_Processing.md and
docs/architecture/specification/91_Background_Processing.md. Workers
orchestrate calls into domain/application services; they contain no
business rules of their own.
"""
