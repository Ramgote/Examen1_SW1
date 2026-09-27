import { BaseEdge, getSmoothStepPath, useNodes } from '@xyflow/react'
import { associationNode, associationLink } from './associationClass.js'

export function RelationEdge(props) {
  const { id, sourceX, sourceY, targetX, targetY, source, target, selected, data } = props
  let [path, labelX, labelY] = getSmoothStepPath(props)
  const nodes = useNodes()

  if (source === target) {
    const top = Math.min(sourceY, targetY) - 130
    path = `M ${sourceX} ${sourceY} C ${sourceX + 100} ${top}, ${targetX - 100} ${top}, ${targetX} ${targetY}`
    labelX = (sourceX + targetX) / 2
    labelY = top + 30
  }

  const isComposition = data.type === 'composition'
  const isAggregation = data.type === 'aggregation'
  const isGeneralization = data.type === 'generalization'
  const isRealization = data.type === 'realization'
  const isTemplateBinding = data.type === 'template_binding'
  const isDependency = data.type === 'dependency'
  const isAssociationClass = data.type === 'association_class'
  const isAssociation = data.type === 'association' || !data.type

  const isDashed = isRealization || isTemplateBinding || isDependency

  const markerStartId = `uml-marker-start-${id}`
  const markerEndId = `uml-marker-end-${id}`
  const strokeColor = selected ? '#0051d5' : '#0b1c30'
  const strokeWidth = selected ? 2.2 : 1.5

  const showCardinalities = !isGeneralization && !isRealization && !isDependency && !isTemplateBinding

  const assocNode = isAssociationClass ? associationNode(nodes, data) : null
  const assocLinePath = assocNode ? associationLink(assocNode, labelX, labelY) : null

  return (
    <>
      <defs>
        {/* Marcadores de Inicio (Source: Diamantes para Composición / Agregación) */}
        {(isComposition || isAggregation) && (
          <marker
            id={markerStartId}
            viewBox="0 0 20 14"
            markerWidth="16"
            markerHeight="12"
            refX="0"
            refY="7"
            orient="auto"
            markerUnits="userSpaceOnUse"
          >
            {isComposition ? (
              <polygon points="0,7 10,1 20,7 10,13" fill="#0b1c30" stroke="#0b1c30" strokeWidth="1.2" />
            ) : (
              <polygon points="0,7 10,1 20,7 10,13" fill="#ffffff" stroke="#0b1c30" strokeWidth="1.5" />
            )}
          </marker>
        )}

        {/* Marcadores de Fin (Target: Triángulos para Herencia/Realización, Flechas abiertas para Asociación/Dependencia/Binding) */}
        {(isGeneralization || isRealization) && (
          <marker
            id={markerEndId}
            viewBox="0 0 20 14"
            markerWidth="16"
            markerHeight="12"
            refX="18"
            refY="7"
            orient="auto"
            markerUnits="userSpaceOnUse"
          >
            <polygon points="0,1 18,7 0,13" fill="#ffffff" stroke="#0b1c30" strokeWidth="1.5" />
          </marker>
        )}

        {(isAssociation || isDependency || isTemplateBinding || isAssociationClass) && (
          <marker
            id={markerEndId}
            viewBox="0 0 20 14"
            markerWidth="14"
            markerHeight="12"
            refX="14"
            refY="7"
            orient="auto"
            markerUnits="userSpaceOnUse"
          >
            <path d="M 0 1 L 14 7 L 0 13" fill="none" stroke="#0b1c30" strokeWidth="1.6" strokeLinecap="round" />
          </marker>
        )}
      </defs>

      {/* Línea discontinua conectando al nodo de AssociationClass */}
      {assocLinePath && (
        <g className="uml-association-class-link pointer-events-none">
          <path
            d={assocLinePath}
            stroke={strokeColor}
            strokeWidth="1.4"
            strokeDasharray="4 3"
            fill="none"
          />
        </g>
      )}

      <BaseEdge
        id={id}
        path={path}
        markerStart={isComposition || isAggregation ? `url(#${markerStartId})` : undefined}
        markerEnd={
          isGeneralization || isRealization || isDependency || isTemplateBinding
            ? `url(#${markerEndId})`
            : undefined
        }
        style={{
          stroke: strokeColor,
          strokeWidth: strokeWidth,
          strokeDasharray: isDashed ? '6 4' : undefined,
        }}
      />

      {/* Textos, Estereotipos y Multiplicidades */}
      <g className="uml-edge-text font-mono text-[11px] select-none pointer-events-none">
        {!(isAssociationClass && assocNode) && (data.relation_name || isTemplateBinding || isAssociationClass) && (
          <text
            x={labelX}
            y={labelY - 8}
            textAnchor="middle"
            className="fill-secondary font-semibold text-[10px]"
            style={{ paintOrder: 'stroke', stroke: '#ffffff', strokeWidth: '3px', strokeLinejoin: 'round' }}
          >
            {isTemplateBinding
              ? data.relation_name ? `«bind» ${data.relation_name}` : '«bind»'
              : isAssociationClass
              ? data.relation_name ? `«association class» ${data.relation_name}` : '«association class»'
              : data.relation_name}
          </text>
        )}
        {showCardinalities && (
          <>
            <text
              x={sourceX + 24}
              y={sourceY - 10}
              textAnchor="start"
              className="fill-on-surface font-bold text-[11px]"
              style={{ paintOrder: 'stroke', stroke: '#ffffff', strokeWidth: '3px', strokeLinejoin: 'round' }}
            >
              {data.source_cardinality} {data.source_role ? `(${data.source_role})` : ''}
            </text>
            <text
              x={targetX - 24}
              y={targetY - 10}
              textAnchor="end"
              className="fill-on-surface font-bold text-[11px]"
              style={{ paintOrder: 'stroke', stroke: '#ffffff', strokeWidth: '3px', strokeLinejoin: 'round' }}
            >
              {data.target_cardinality} {data.target_role ? `(${data.target_role})` : ''}
            </text>
          </>
        )}
      </g>
    </>
  )
}
