<template>
  <div class="graph-canvas-container" ref="rootEl">
    <div v-show="graphData.nodes.length > 0" class="graph-canvas" ref="container"></div>
    <div class="slots">
      <div v-if="$slots.top" class="overlay top">
        <slot name="top" />
      </div>
      <div class="canvas-content">
        <slot name="content" />
      </div>
      <!-- Statistical Info Panel -->
      <div class="graph-stats-panel" v-if="graphData.nodes.length > 0">
        <div class="stat-item">
          <span class="stat-label">节点</span>
          <span class="stat-value">{{ graphData.nodes.length }}</span>
          <span v-if="graphInfo?.node_count" class="stat-total">/ {{ graphInfo.node_count }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">边</span>
          <span class="stat-value">{{ graphData.edges.length }}</span>
          <span v-if="graphInfo?.edge_count" class="stat-total">/ {{ graphInfo.edge_count }}</span>
        </div>
      </div>
      <div v-if="$slots.bottom" class="overlay bottom">
        <slot name="bottom" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { Graph } from '@antv/g6'
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useThemeStore } from '@/stores/theme'

// 选中状态管理
const selectedEdgeId = ref(null)
//
const selectedNodeId = ref(null)
// 可见关系边 ID 集合
const visibleRelationEdgeIds = ref(new Set())
// 可见邻居节点 ID 集合
const visibleNeighborNodeIds = ref(new Set())
// 节点点击模式：soft = 第一次点击形式；strong = 第二次点击高亮形式
const nodeFocusMode = ref('soft')

const props = defineProps({
  graphData: {
    type: Object,
    required: true,
    default: () => ({ nodes: [], edges: [] })
  },
  graphInfo: {
    type: Object,
    default: () => ({})
  },
  labelField: { type: String, default: 'name' },
  autoFit: { type: Boolean, default: true },
  autoResize: { type: Boolean, default: true },
  layoutOptions: { type: Object, default: () => ({}) },
  nodeStyleOptions: { type: Object, default: () => ({}) },
  edgeStyleOptions: { type: Object, default: () => ({}) },
  enableFocusNeighbor: { type: Boolean, default: true },
  sizeByDegree: { type: Boolean, default: true },
  highlightKeywords: { type: Array, default: () => [] }
})

const emit = defineEmits(['ready', 'data-rendered', 'node-click', 'edge-click', 'canvas-click'])

const container = ref(null)
const rootEl = ref(null)
const themeStore = useThemeStore()
let graphInstance = null
let resizeObserver = null
let renderTimeout = null
let retryCount = 0
const MAX_RETRIES = 5
let centerRequestToken = 0

const defaultLayout = {
  type: 'd3-force',
  preventOverlap: true,
  alphaDecay: 0.035,
  alphaMin: 0.001,
  velocityDecay: 0.46,
  iterations: 520,
  force: {
    center: { x: 0.5, y: 0.5, strength: 0.025 },
    charge: { strength: -1250, distanceMax: 1300 },
    link: { distance: 150, strength: 0.16 }
  },
  collide: { radius: 46, strength: 1, iterations: 6 }
}

// CSS 变量解析工具函数
function getCSSVariable(variableName, element = document.documentElement) {
  return getComputedStyle(element).getPropertyValue(variableName).trim()
}

// 新增函数：标签截断工具，避免过长文本导致布局混乱
function truncateLabel(value, maxLength = 18) {
  const text = String(value ?? '')
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength)}…`
}
// 新增函数：边标签生成工具，根据关系类型数量智能显示标签内容
function getEdgeRelationLabel(edgeDatum) {
  const relationTypes = edgeDatum.data?.relationTypes || []

  if (relationTypes.length === 0) {
    return (
      edgeDatum.data?.label ||
      edgeDatum.data?.original?.type ||
      edgeDatum.data?.original?.name ||
      ''
    )
  }

  if (relationTypes.length === 1) {
    return relationTypes[0]
  }

  return `${relationTypes[0]} +${relationTypes.length - 1}`
}

// 新增函数：文本规范化工具，统一转换为小写字符串，便于关键词匹配
function normalizeText(value) {
  return String(value ?? '').toLowerCase()
}

// 新增函数：根据节点属性和标签内容推断节点类别，便于后续根据类别调整样式或行为
function inferNodeCategory(node, label) {
  const raw = [
    node.id,
    node.name,
    node.type,
    node.label,
    node.display_type,
    node.title,
    ...(Array.isArray(node.labels) ? node.labels : [])
  ]
    .map(normalizeText)
    .join(' ')

  const text = `${normalizeText(label)} ${raw}`

  if (text.includes('flavonoid content') || text.includes('黄酮')) return 'trait'
  if (
    text.includes('foxtail millet') ||
    text.includes('setaria') ||
    text.includes('crop') ||
    text.includes('谷子')
  )
    return 'crop'

  if (/si\d+g\d+\.\d+/i.test(String(label)) || text.includes('gene')) return 'gene'

  if (
    text.includes('snp') ||
    text.includes('indel') ||
    text.includes('kasp') ||
    text.includes('caps') ||
    text.includes('marker') ||
    text.includes('标记')
  ) {
    return 'marker'
  }

  if (
    text.includes('transcriptomics') ||
    text.includes('metabolomics') ||
    text.includes('annotation') ||
    text.includes('evidence') ||
    text.includes('转录') ||
    text.includes('代谢') ||
    text.includes('注释') ||
    text.includes('证据')
  ) {
    return 'evidence'
  }

  if (
    text.includes('validation') ||
    text.includes('population') ||
    text.includes('群体') ||
    text.includes('验证')
  ) {
    return 'validation'
  }

  if (
    text.includes('doi') ||
    text.includes('paper') ||
    text.includes('literature') ||
    text.includes('文献')
  ) {
    return 'paper'
  }

  return 'other'
}

function sortBusinessNodes(nodes) {
  const geneOrder = ['Si9g04210.1', 'Si5g31340.1', 'Si9g34380.1']
  const markerOrder = ['SNP', 'InDel', 'KASP', 'CAPS']

  return [...nodes].sort((a, b) => {
    const aLabel = String(a.data?.label ?? '')
    const bLabel = String(b.data?.label ?? '')

    const aGeneIndex = geneOrder.findIndex((g) => aLabel.includes(g))
    const bGeneIndex = geneOrder.findIndex((g) => bLabel.includes(g))
    if (aGeneIndex !== -1 || bGeneIndex !== -1) {
      return (aGeneIndex === -1 ? 999 : aGeneIndex) - (bGeneIndex === -1 ? 999 : bGeneIndex)
    }

    const aMarkerIndex = markerOrder.findIndex((m) =>
      aLabel.toLowerCase().includes(m.toLowerCase())
    )
    const bMarkerIndex = markerOrder.findIndex((m) =>
      bLabel.toLowerCase().includes(m.toLowerCase())
    )
    if (aMarkerIndex !== -1 || bMarkerIndex !== -1) {
      return (aMarkerIndex === -1 ? 999 : aMarkerIndex) - (bMarkerIndex === -1 ? 999 : bMarkerIndex)
    }

    return aLabel.localeCompare(bLabel)
  })
}

function placeRow(items, y, leftX, rightX) {
  if (items.length === 0) return
  if (items.length === 1) {
    items[0].style = { ...(items[0].style || {}), x: (leftX + rightX) / 2, y }
    return
  }

  const gap = (rightX - leftX) / (items.length - 1)
  items.forEach((item, index) => {
    item.style = {
      ...(item.style || {}),
      x: leftX + gap * index,
      y
    }
  })
}

function applyBusinessLayeredPositions(nodes) {
  const width = container.value?.offsetWidth || 1000
  const height = container.value?.offsetHeight || 720

  const cx = width / 2
  const top = Math.max(90, height * 0.12)
  const traitY = Math.max(190, height * 0.26)
  const geneY = Math.max(330, height * 0.44)
  const markerY = Math.max(500, height * 0.66)
  const evidenceY = Math.max(250, height * 0.34)
  const bottomY = Math.max(640, height * 0.84)

  const groups = {
    crop: [],
    trait: [],
    gene: [],
    marker: [],
    evidence: [],
    validation: [],
    paper: [],
    other: []
  }

  nodes.forEach((node) => {
    const category = node.data?.category || 'other'
    if (!groups[category]) groups.other.push(node)
    else groups[category].push(node)
  })

  Object.keys(groups).forEach((key) => {
    groups[key] = sortBusinessNodes(groups[key])
  })

  placeRow(groups.crop, top, cx - 80, cx + 80)
  placeRow(groups.trait, traitY, cx - 80, cx + 80)

  placeRow(groups.gene, geneY, cx - 330, cx + 330)

  placeRow(groups.marker, markerY, cx - 430, cx + 430)

  const evidenceLeft = groups.evidence.filter((n, index) => index % 2 === 0)
  const evidenceRight = groups.evidence.filter((n, index) => index % 2 === 1)

  placeRow(evidenceLeft, evidenceY, cx - 500, cx - 250)
  placeRow(evidenceRight, evidenceY, cx + 250, cx + 500)

  placeRow(groups.paper, traitY - 70, cx + 260, cx + 500)
  placeRow(groups.validation, bottomY, cx - 180, cx + 180)

  placeRow(groups.other, bottomY, cx - 460, cx + 460)

  return nodes
}

function formatData() {
  const data = props.graphData || { nodes: [], edges: [] }

  // 1. 先聚合边：同一对节点之间只画一条边
  // 注意：这不是删除关系，而是把多条关系收进 data.originals 里
  const edgeMap = new Map()

  for (const e of data.edges || []) {
    const source = String(e.source_id)
    const target = String(e.target_id)

    if (!source || !target || source === 'undefined' || target === 'undefined') continue

    // 当前已经去掉箭头，视觉上按无向边聚合
    // 如果以后要区分方向，可以改成 `${source}__${target}`
    const key = [source, target].sort().join('__')
    const relationType = e.type ?? e.name ?? e.label ?? 'RELATED_TO'

    if (!edgeMap.has(key)) {
      edgeMap.set(key, {
        id: `merged-edge-${edgeMap.size}`,
        source,
        target,
        data: {
          label: relationType,
          relationTypes: [],
          relationCount: 0,
          originals: []
        }
      })
    }

    const merged = edgeMap.get(key)

    if (!merged.data.relationTypes.includes(relationType)) {
      merged.data.relationTypes.push(relationType)
    }

    merged.data.relationCount += 1
    merged.data.originals.push(e)

    merged.data.label =
      merged.data.relationTypes.length > 1
        ? `${merged.data.relationTypes[0]} +${merged.data.relationTypes.length - 1}`
        : merged.data.relationTypes[0]
  }

  const edges = Array.from(edgeMap.values())

  // 2. degree 按“聚合后的可视边”统计，而不是按原始 904 条边统计
  // 否则节点会被撑得过大
  const degrees = new Map()

  for (const n of data.nodes || []) {
    degrees.set(String(n.id), 0)
  }

  for (const e of edges) {
    const s = String(e.source)
    const t = String(e.target)

    degrees.set(s, (degrees.get(s) || 0) + 1)
    degrees.set(t, (degrees.get(t) || 0) + 1)
  }

  // 3. 节点只做基础格式化，不再做业务分层坐标
  // 这样才能形成用户上传未知图谱时的自然无规则力导向布局
  const nodes = (data.nodes || []).map((n) => {
    const fullLabel = n[props.labelField] ?? n.name ?? n.title ?? String(n.id)

    return {
      id: String(n.id),
      data: {
        label: fullLabel,
        displayLabel: truncateLabel(fullLabel, 18),
        degree: degrees.get(String(n.id)) || 0,
        original: n,
        entity_type:
          n.entity_type || n.properties?.entity_type || n.properties?.properties?.entity_type || '',
        display_type:
          n.display_type || n.properties?.display_type || n.properties?.properties?.display_type || '',
        type: n.type || ''
      }
    }
  })

  return { nodes, edges }
}

async function applyCurrentSelectionState() {
  if (!graphInstance) return

  const { nodes, edges } = graphInstance.getData()

  const activeNodeId = selectedNodeId.value ? String(selectedNodeId.value) : ''
  const activeEdgeId = selectedEdgeId.value ? String(selectedEdgeId.value) : ''

  const visibleNodeIds = visibleNeighborNodeIds.value || new Set()
  const visibleEdgeIds = visibleRelationEdgeIds.value || new Set()

  const hasSelection = Boolean(activeNodeId || activeEdgeId)
  const isStrongNodeMode = activeNodeId && nodeFocusMode.value === 'strong'

  const updates = {}

  nodes.forEach((node) => {
    const nodeId = String(node.id)

    if (activeNodeId && nodeId === activeNodeId) {
      updates[node.id] = isStrongNodeMode ? ['selectedStrong'] : ['selected']
    } else if (visibleNodeIds.has(nodeId)) {
      updates[node.id] = isStrongNodeMode ? ['neighborStrong'] : ['focus']
    } else if (hasSelection) {
      updates[node.id] = ['hidden']
    } else {
      updates[node.id] = []
    }
  })

  edges.forEach((edge) => {
    const edgeId = String(edge.id)

    if (activeEdgeId && edgeId === activeEdgeId) {
      updates[edge.id] = ['selected']
    } else if (visibleEdgeIds.has(edgeId)) {
      updates[edge.id] = isStrongNodeMode ? ['edgeStrong'] : ['focus']
    } else if (hasSelection) {
      updates[edge.id] = ['hidden']
    } else {
      updates[edge.id] = []
    }
  })

  await graphInstance.setElementState(updates)
  await graphInstance.draw()
}

// 新增函数：聚焦节点及其邻居，突出显示相关关系，隐藏无关元素
async function focusNeighborhood(nodeId, mode = 'soft') {
  if (!graphInstance) return

  const id = String(nodeId)
  const { edges } = graphInstance.getData()

  const visibleNodeIds = new Set([id])
  const visibleEdgeIds = new Set()

  edges.forEach((edge) => {
    const source = String(edge.source)
    const target = String(edge.target)

    if (source === id || target === id) {
      visibleEdgeIds.add(String(edge.id))
      visibleNodeIds.add(source)
      visibleNodeIds.add(target)
    }
  })

  selectedNodeId.value = id
  selectedEdgeId.value = null
  nodeFocusMode.value = mode
  visibleRelationEdgeIds.value = visibleEdgeIds
  visibleNeighborNodeIds.value = visibleNodeIds

  await applyCurrentSelectionState()
}

// 新增函数：从详情面板聚焦节点，复用 focusNeighborhood 功能
function resolveRenderedNodeId(nodeId) {
  if (!graphInstance || !nodeId) return ''

  const id = String(nodeId)
  const { nodes } = graphInstance.getData()

  const matched = nodes.find((node) => {
    const values = [
      node.id,
      node.data?.label,
      node.data?.displayLabel,
      node.data?.original?.id,
      node.data?.original?.name,
      node.data?.original?.title
    ]
      .filter(Boolean)
      .map(String)

    return values.includes(id)
  })

  return matched ? String(matched.id) : id
}

async function focusNodeFromDetail(nodeId) {
  const id = resolveRenderedNodeId(nodeId)
  if (!id) return

  const mode =
    selectedNodeId.value === id && nodeFocusMode.value === 'strong' ? 'strong' : 'soft'

  await focusNeighborhood(id, mode)

  setTimeout(() => {
    centerNodeInCanvas(id)
  }, 80)
}

async function focusEdgeFromDetail(edgePayload) {
  if (!graphInstance) return

  const payload =
    typeof edgePayload === 'object' && edgePayload !== null
      ? edgePayload
      : { id: String(edgePayload) }

  const { edges } = graphInstance.getData()

  const payloadId = payload.id ? String(payload.id) : ''
  const payloadSource = payload.source ? String(payload.source) : ''
  const payloadTarget = payload.target ? String(payload.target) : ''

  const matched = edges.find((edge) => {
    if (payloadId && String(edge.id) === payloadId) return true

    const sameDirection =
      String(edge.source) === payloadSource && String(edge.target) === payloadTarget

    const reverseDirection =
      String(edge.source) === payloadTarget && String(edge.target) === payloadSource

    return sameDirection || reverseDirection
  })

  if (!matched) return

  await focusSingleEdge(matched.id)

  setTimeout(() => {
    centerEdgeInCanvas(matched)
  }, 40)
}

// 新增函数：聚焦单条边及其两个端点，突出显示该关系，隐藏无关元素
async function focusSingleEdge(edgeId) {
  if (!graphInstance) return

  const id = String(edgeId)
  const { edges } = graphInstance.getData()
  const currentEdge = edges.find((edge) => String(edge.id) === id)

  if (!currentEdge) return

  selectedNodeId.value = null
  selectedEdgeId.value = id
  nodeFocusMode.value = 'soft'

  visibleRelationEdgeIds.value = new Set([id])
  visibleNeighborNodeIds.value = new Set([String(currentEdge.source), String(currentEdge.target)])

  await applyCurrentSelectionState()
}
// 新增函数：清除所有选中和聚焦状态，恢复默认显示，适用于用户点击空白处或重置视图时
async function clearGraphSelection() {
  if (!graphInstance) return

  selectedNodeId.value = null
  selectedEdgeId.value = null
  nodeFocusMode.value = 'soft'
  visibleRelationEdgeIds.value = new Set()
  visibleNeighborNodeIds.value = new Set()

  await applyCurrentSelectionState()
}

function initGraph() {
  if (!container.value) return

  const width = container.value.offsetWidth
  const height = container.value.offsetHeight

  if (width === 0 && height === 0) {
    if (retryCount < MAX_RETRIES) {
      retryCount++
      clearTimeout(renderTimeout)
      renderTimeout = setTimeout(initGraph, 200)
    }
    return
  }

  retryCount = 0
  container.value.innerHTML = ''

  if (graphInstance) {
    try {
      graphInstance.destroy()
    } catch {
      // ignore cleanup error
    }
    graphInstance = null
  }

  graphInstance = new Graph({
    container: container.value,
    width,
    height,
    autoFit: props.autoFit,
    autoResize: props.autoResize,
    layout: { ...defaultLayout, ...props.layoutOptions },
    node: {
      type: 'circle',
      style: {
        ...(props.nodeStyleOptions.style || {}),

        labelText: (d) => {
          const nodeId = String(d.id)
          const deg = d.data.degree || 0

          // 当前选中节点：必须显示完整名称，不省略
          if (selectedNodeId.value && nodeId === String(selectedNodeId.value)) {
            return d.data.label || d.data.displayLabel
          }

          // 一阶邻居：显示短标签，避免画面过乱
          if (selectedNodeId.value && visibleNeighborNodeIds.value.has(nodeId)) {
            return d.data.displayLabel || d.data.label
          }

          // 默认状态：只显示高连接节点短标签
          if (deg < 5) return ''

          return d.data.displayLabel || d.data.label
        },
        labelFill: '#475569',
        labelFontSize: 10,
        labelWordWrap: false,

        labelMaxWidth: (d) => {
          const nodeId = String(d.id)
          if (selectedNodeId.value && nodeId === String(selectedNodeId.value)) return 260
          return 110
        },
        labelWordWrap: (d) => {
          const nodeId = String(d.id)
          return Boolean(selectedNodeId.value && nodeId === String(selectedNodeId.value))
        },

        size: (d) => {
          if (!props.sizeByDegree) return 20
          const deg = d.data.degree || 0
          return Math.min(18 + Math.sqrt(deg) * 5.5, 38)
        },

        fill: '#e6f4ff',
        stroke: '#1677ff',
        lineWidth: 1.5,
        opacity: 0.95,

        shadowColor: 'rgba(22, 119, 255, 0.12)',
        shadowBlur: 4
      },
      state: {
        selected: {
          fill: '#e6f4ff',
          stroke: '#1677ff',
          lineWidth: 2.4,
          opacity: 1,
          labelFill: '#0f172a',
          shadowColor: 'rgba(22, 119, 255, 0.22)',
          shadowBlur: 10
        },
        active: {
          fill: '#e6f4ff',
          stroke: '#1677ff',
          lineWidth: 1.8,
          opacity: 1,
          labelFill: '#334155'
        },
        inactive: {
          opacity: 0.28,
          labelFill: '#94a3b8'
        },
        focus: {
          fill: '#e6f4ff',
          stroke: '#1677ff',
          lineWidth: 1.5,
          opacity: 0.95,
          labelFill: '#475569',
          shadowColor: 'rgba(22, 119, 255, 0.10)',
          shadowBlur: 4
        },
        hidden: {
          opacity: 0.24,
          labelFill: '#94a3b8'
        },
        highlighted: {
          fill: '#e6f4ff',
          stroke: '#1677ff',
          lineWidth: 2,
          opacity: 1,
          labelFill: '#0f172a',
          shadowColor: 'rgba(22, 119, 255, 0.16)',
          shadowBlur: 8
        },
        selectedStrong: {
          fill: '#1677ff',
          stroke: '#0958d9',
          lineWidth: 2.6,
          opacity: 1,
          labelFill: '#0f172a',
          shadowColor: 'rgba(22, 119, 255, 0.32)',
          shadowBlur: 16
        },
        neighborStrong: {
          fill: '#dbeafe',
          stroke: '#1677ff',
          lineWidth: 2,
          opacity: 1,
          labelFill: '#334155',
          shadowColor: 'rgba(22, 119, 255, 0.16)',
          shadowBlur: 8
        }
      }
    },
    edge: {
      type: 'line',
      style: {
        ...(props.edgeStyleOptions.style || {}),

        labelText: (d) => {
          const shouldShow = selectedEdgeId.value === d.id || visibleRelationEdgeIds.value.has(d.id)

          if (!shouldShow) return ''

          return getEdgeRelationLabel(d)
        },
        labelFill: '#64748b',
        labelFontSize: 9,
        labelFontWeight: 500,
        labelBackground: true,
        labelBackgroundFill: 'rgba(255, 255, 255, 0.92)',
        labelBackgroundStroke: '#bfdbfe',
        labelBackgroundRadius: 4,

        stroke: '#8fa3c2',
        opacity: 0.5,
        lineWidth: 0.9,
        startArrow: false,
        endArrow: false
      },
      state: {
        selected: {
          stroke: '#1677ff',
          opacity: 1,
          lineWidth: 1.8,
          labelFill: '#64748b',
          labelFontSize: 9,
          labelFontWeight: 500,
          shadowColor: 'rgba(22, 119, 255, 0.18)',
          shadowBlur: 6
        },
        active: {
          stroke: '#64748b',
          opacity: 0.85,
          lineWidth: 1.2,
          labelFill: '#64748b',
          labelFontSize: 9,
          labelFontWeight: 500
        },
        inactive: {
          opacity: 0.16
        },
        hidden: {
          opacity: 0.08
        },
        focus: {
          stroke: '#8fa3c2',
          opacity: 0.9,
          lineWidth: 1.2,
          labelFill: '#64748b',
          labelFontSize: 9,
          labelFontWeight: 500
        },
        edgeStrong: {
          stroke: '#1677ff',
          opacity: 1,
          lineWidth: 1.9,
          labelFill: '#64748b',
          labelFontSize: 9,
          labelFontWeight: 500,
          shadowColor: 'rgba(22, 119, 255, 0.22)',
          shadowBlur: 8
        }
      }
    },
    behaviors: ['drag-element', 'zoom-canvas', 'drag-canvas']
  })

  // 绑定事件
  graphInstance.on('node:click', async (evt) => {
    const { target } = evt
    const nodeId = String(target.id)
    const nodeData = graphInstance.getNodeData(nodeId)

    // 同节点：soft → strong，之后保持 strong；切节点：始终 soft
    const mode =
      selectedEdgeId.value === null && selectedNodeId.value === nodeId ? 'strong' : 'soft'

    await focusNeighborhood(nodeId, mode)

    emit('node-click', nodeData)
  })
  graphInstance.on('edge:click', async (evt) => {
    const { target } = evt
    const edgeId = target.id
    const edgeData = graphInstance.getEdgeData(edgeId)

    await focusSingleEdge(edgeId)

    emit('edge-click', edgeData)
  })

  graphInstance.on('canvas:click', async (evt) => {
    if (!evt.target) {
      await clearGraphSelection()
      emit('canvas-click')
    }
  })

  // graphInstance.on('edge:click', (evt) => {
  //   const { target } = evt
  //   const edgeId = target.id
  //   const edgeData = graphInstance.getEdgeData(edgeId)
  //   emit('edge-click', edgeData)
  // })

  // graphInstance.on('canvas:click', (evt) => {
  //   // 只有点击画布空白处才触发
  //   if (!evt.target) {
  //     emit('canvas-click')
  //   }
  // })

  emit('ready', graphInstance)
}

function setGraphData() {
  if (!graphInstance) initGraph()
  if (!graphInstance) return
  const data = formatData()

  console.log('开始设置图谱数据:', {
    nodes: data.nodes.length,
    edges: data.edges.length
  })

  graphInstance.setData(data)
  graphInstance.render()

  // 手动触发布局重新计算，确保节点分布
  setTimeout(() => {
    try {
      if (graphInstance && graphInstance.layout) {
        graphInstance.layout()
        console.log('触发布局重新计算')
      }
    } catch (error) {
      console.warn('布局重新计算失败:', error)
    }

    // 等待力导向布局稳定后再应用高亮
    setTimeout(() => {
      applyHighlightKeywords()
      emit('data-rendered')
      console.log('图谱渲染完成')
    }, 100)
  }, 10) // 等待 10ms 确保布局完成
}

// 关键词高亮功能
function applyHighlightKeywords() {
  if (!graphInstance || !props.highlightKeywords || props.highlightKeywords.length === 0) return

  const { nodes } = graphInstance.getData()
  const updates = {}

  nodes.forEach((node) => {
    const nodeLabel = node.data.label || node.data[props.labelField] || String(node.id)
    const shouldHighlight = props.highlightKeywords.some(
      (keyword) => keyword.trim() !== '' && nodeLabel.toLowerCase().includes(keyword.toLowerCase())
    )

    if (shouldHighlight) {
      updates[node.id] = ['highlighted']
    }
  })

  if (Object.keys(updates).length > 0) {
    graphInstance.setElementState(updates)
    graphInstance.draw()
  }
}

// 清除高亮
function clearHighlights() {
  if (!graphInstance) return

  const { nodes } = graphInstance.getData()
  const updates = {}

  nodes.forEach((node) => {
    updates[node.id] = []
  })

  if (Object.keys(updates).length > 0) {
    graphInstance.setElementState(updates)
    graphInstance.draw()
  }
}

function renderGraph() {
  if (!graphInstance) initGraph()
  setGraphData()
}

function refreshGraph() {
  if (graphInstance) {
    try {
      graphInstance.destroy()
    } catch {
      // ignore cleanup error
    }
    graphInstance = null
  }
  if (container.value) container.value.innerHTML = ''
  retryCount = 0
  clearTimeout(renderTimeout)
  renderTimeout = setTimeout(() => {
    renderGraph()
  }, 300)
}

function fitView() {
  if (graphInstance)
    try {
      graphInstance.fitView()
    } catch {
      // ignore
    }
}
function fitCenter() {
  if (graphInstance)
    try {
      graphInstance.fitCenter()
    } catch {
      // ignore
    }
}

async function fitGraphToCurrentCanvas() {
  if (!graphInstance || !container.value) return

  await resizeToContainer()

  try {
    if (typeof graphInstance.fitView === 'function') {
      await graphInstance.fitView({
        padding: 80,
        animation: {
          duration: 320,
          easing: 'ease-in-out'
        }
      })
      return
    }
  } catch (error) {
    console.warn('fitView(options) failed:', error)
  }

  try {
    if (typeof graphInstance.fitView === 'function') {
      await graphInstance.fitView()
      return
    }
  } catch (error) {
    console.warn('fitView() failed:', error)
  }

  try {
    if (typeof graphInstance.fitCenter === 'function') {
      await graphInstance.fitCenter()
    }
  } catch (error) {
    console.warn('fitCenter failed:', error)
  }
}

function waitFrames(count = 2) {
  return new Promise((resolve) => {
    let remaining = count

    const step = () => {
      remaining -= 1
      if (remaining <= 0) {
        resolve()
        return
      }

      requestAnimationFrame(step)
    }

    requestAnimationFrame(step)
  })
}

async function resizeToContainer() {
  if (!graphInstance || !container.value) return

  await waitFrames(2)

  const width = container.value.offsetWidth
  const height = container.value.offsetHeight

  if (!width || !height) return

  try {
    if (typeof graphInstance.setSize === 'function') {
      await graphInstance.setSize(width, height)
    } else if (typeof graphInstance.changeSize === 'function') {
      graphInstance.changeSize(width, height)
    } else if (typeof graphInstance.resize === 'function') {
      graphInstance.resize(width, height)
    }
  } catch (error) {
    console.warn('resize graph to container failed:', error)
  }

  await waitFrames(2)
}

function restoreSelectionAfterViewportMove(token, delay = 360) {
  requestAnimationFrame(() => {
    if (token !== centerRequestToken) return
    applyCurrentSelectionState()
  })

  window.setTimeout(() => {
    if (token !== centerRequestToken) return
    applyCurrentSelectionState()
  }, delay)
}

async function centerNodeInCanvas(nodeId) {
  if (!graphInstance || !nodeId) return

  const id = String(nodeId)
  const token = ++centerRequestToken

  await resizeToContainer()

  try {
    if (typeof graphInstance.focusElement === 'function') {
      await graphInstance.focusElement(id, {
        animation: {
          duration: 320,
          easing: 'ease-in-out'
        }
      })

      restoreSelectionAfterViewportMove(token, 360)
      return
    }
  } catch (error) {
    console.warn('focusElement(options) failed:', error)
  }

  try {
    if (typeof graphInstance.focusElement === 'function') {
      await graphInstance.focusElement(id, true)

      restoreSelectionAfterViewportMove(token, 120)
      return
    }
  } catch (error) {
    console.warn('focusElement(boolean) failed:', error)
  }

  try {
    if (typeof graphInstance.fitCenter === 'function') {
      await graphInstance.fitCenter()
    }
  } catch {
    // ignore fallback error
  }

  restoreSelectionAfterViewportMove(token, 120)
}

async function centerEdgeInCanvas(edgePayload) {
  if (!graphInstance || !edgePayload) return

  const token = ++centerRequestToken
  const payload = typeof edgePayload === 'object' ? edgePayload : { id: String(edgePayload) }

  const { edges } = graphInstance.getData()
  const payloadId = payload.id ? String(payload.id) : ''
  const payloadSource = payload.source ? String(payload.source) : ''
  const payloadTarget = payload.target ? String(payload.target) : ''

  const matched = edges.find((edge) => {
    if (payloadId && String(edge.id) === payloadId) return true

    const sameDirection =
      String(edge.source) === payloadSource && String(edge.target) === payloadTarget

    const reverseDirection =
      String(edge.source) === payloadTarget && String(edge.target) === payloadSource

    return sameDirection || reverseDirection
  })

  if (!matched) return

  await resizeToContainer()

  try {
    if (typeof graphInstance.focusElement === 'function') {
      await graphInstance.focusElement(matched.id, {
        animation: {
          duration: 320,
          easing: 'ease-in-out'
        }
      })

      restoreSelectionAfterViewportMove(token, 360)
      return
    }
  } catch (error) {
    console.warn('focus edge failed:', error)
  }

  await centerNodeInCanvas(matched.source)
}

function getInstance() {
  return graphInstance
}

async function focusNode(id) {
  if (!graphInstance || !props.enableFocusNeighbor) return
  const { nodes, edges } = graphInstance.getData()
  const nodeIds = nodes.map((n) => n.id)
  const edgeIds = edges.map((e) => e.id)
  const updates = {}
  nodeIds.forEach((nid) => (updates[nid] = ['hidden']))
  edgeIds.forEach((eid) => (updates[eid] = ['hidden']))
  const neighborSet = new Set()
  const related = []
  edges.forEach((e) => {
    if (e.source === id) {
      neighborSet.add(e.target)
      related.push(e.id)
    } else if (e.target === id) {
      neighborSet.add(e.source)
      related.push(e.id)
    }
  })
  updates[id] = ['focus']
  Array.from(neighborSet).forEach((nid) => (updates[nid] = ['focus']))
  related.forEach((eid) => (updates[eid] = ['focus']))
  await graphInstance.setElementState(updates)
  await graphInstance.draw()
}

async function clearFocus() {
  if (!graphInstance) return
  const { nodes, edges } = graphInstance.getData()
  const nodeIds = nodes.map((n) => n.id)
  const edgeIds = edges.map((e) => e.id)
  const updates = {}
  nodeIds.forEach((nid) => (updates[nid] = []))
  edgeIds.forEach((eid) => (updates[eid] = []))
  await graphInstance.setElementState(updates)
  await graphInstance.draw()
}

watch(
  () => props.graphData,
  () => {
    clearTimeout(renderTimeout)
    renderTimeout = setTimeout(() => setGraphData(), 50)
  },
  { deep: true }
)

// 监听关键词变化
watch(
  () => props.highlightKeywords,
  () => {
    if (graphInstance) {
      clearHighlights()
      setTimeout(() => applyHighlightKeywords(), 50)
    }
  },
  { deep: true }
)

// 监听主题切换，重新加载图形
watch(
  () => themeStore.isDark,
  () => {
    if (graphInstance) {
      refreshGraph()
    }
  }
)

onMounted(() => {
  // ResizeObserver 监听容器尺寸，自动重渲染
  if (window.ResizeObserver) {
    resizeObserver = new ResizeObserver(() => {
      if (!container.value || !graphInstance) return
      const width = container.value.offsetWidth
      const height = container.value.offsetHeight
      graphInstance.changeSize(width, height)
    })
    if (container.value) resizeObserver.observe(container.value)
  }

  clearTimeout(renderTimeout)
  renderTimeout = setTimeout(() => {
    renderGraph()
  }, 300)

  window.addEventListener('resize', refreshGraph)
})

onUnmounted(() => {
  window.removeEventListener('resize', refreshGraph)
  if (resizeObserver && container.value) resizeObserver.unobserve(container.value)
  clearTimeout(renderTimeout)
  try {
    graphInstance?.destroy()
  } catch {
    // ignore cleanup error
  }
  graphInstance = null
})

// 暴露方法
defineExpose({
  refreshGraph,
  fitView,
  fitCenter,
  getInstance,
  focusNode,
  clearFocus,
  clearGraphSelection,
  focusNodeFromDetail,
  focusEdgeFromDetail,
  resizeToContainer,
  centerNodeInCanvas,
  centerEdgeInCanvas,
  fitGraphToCurrentCanvas,
  setData: setGraphData,
  applyHighlightKeywords,
  clearHighlights
})
</script>

<style lang="less">
.graph-canvas-container {
  position: relative;
  width: 100%;
  height: 100%;
  // background-color: var(--gray-0);

  .graph-canvas {
    width: 100%;
    height: 100%;
  }

  .graph-stats-panel {
    // position: absolute;
    // bottom: 20px;
    // left: 20px;
    // display: flex;
    // align-items: center;
    // gap: 16px;
    // padding: 8px 14px;
    // background: var(--color-trans-light);
    // border: 1px solid var(--color-border-secondary);
    // border-radius: 8px;
    // box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    // pointer-events: auto;
    // z-index: 10;
    // font-size: 13px;
    // backdrop-filter: blur(4px);
    position: absolute;
    bottom: 20px;
    left: 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 8px 14px;
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
    pointer-events: auto;
    z-index: 10;
    font-size: 13px;
    backdrop-filter: blur(8px);

    .stat-item {
      display: flex;
      align-items: center;
      gap: 4px;

      .stat-label {
        color: var(--color-text-secondary);
        font-weight: 500;
      }

      .stat-value {
        color: var(--color-text);
        font-weight: 600;
      }

      .stat-total {
        color: var(--color-text-quaternary);
        font-size: 11px;
      }
    }
  }

  .slots {
    // 让整层覆盖容器默认不接收指针事件（便于穿透到底下画布）
    pointer-events: none;
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    z-index: 999;

    .overlay {
      width: 100%;
      flex-shrink: 0;
      flex-grow: 0;
      pointer-events: auto;

      &.top {
        top: 0;
      }
      &.bottom {
        bottom: 0;
      }
    }
    .canvas-content {
      // 中间内容层及其子元素全部穿透
      pointer-events: none;
      flex: 1;
      background: transparent !important;
    }
    .canvas-content * {
      pointer-events: none;
    }
  }
}

/* 高亮节点的脉冲动画效果 */
@keyframes highlightPulse {
  0% {
    filter: brightness(1);
  }
  50% {
    filter: brightness(1.15) drop-shadow(0 0 8px rgba(22, 119, 255, 0.45));
  }
  100% {
    filter: brightness(1);
  }
}

.highlight-animation {
  animation: highlightPulse 2s infinite ease-in-out;
}
</style>
