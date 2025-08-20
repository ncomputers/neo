# Order Status

This module centralizes allowed order states and the transitions between them.

| From        | To                                      |
|-------------|-----------------------------------------|
| placed      | accepted, rejected, hold                |
| accepted    | in_progress, ready, cancelled           |
| in_progress | ready, cancelled                        |
| ready       | served, cancelled                       |
| served      | -                                       |
| cancelled   | -                                       |
| rejected    | -                                       |
| hold        | accepted, rejected, cancelled           |
