from app.schemas.uml import UMLCanvasDiagram


def document(snapshot):
    metadata = dict(snapshot.metadata_info)
    schema_version = metadata.pop('schema_version', 1)
    return UMLCanvasDiagram(schema_version=schema_version, version=snapshot.version,
                            nodes=snapshot.nodes, edges=snapshot.edges, metadata=metadata)
