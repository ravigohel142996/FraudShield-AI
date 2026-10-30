"""RAGShield Eval — a benchmark for indirect prompt injection and retrieval authorisation.

Two independent tracks:

Track A (model behaviour)      src/graders.py          -> does the model treat retrieved
                                                          text as data?
Track B (retrieval authority)  src/authorization_engine.py + src/retrieval_simulator.py
                                                       -> does the application ever put a
                                                          document it should not into the
                                                          model's context?
"""

__version__ = "1.0.0"
