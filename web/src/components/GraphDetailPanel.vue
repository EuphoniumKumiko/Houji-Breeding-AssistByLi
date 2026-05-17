<template>
  <section v-if="visible" class="kg-detail-card">
    <header class="kg-detail-hero">
      <button class="close-btn" type="button" @click.stop="emit('close')" aria-label="关闭详情面板">
        <span>×</span>
      </button>

      <div class="hero-main">
        <div class="avatar">{{ avatarText }}</div>

        <div class="hero-text">
          <div class="eyebrow">{{ panelTitle }}</div>
          <h3 class="entity-title" :title="displayTitle">{{ displayTitle }}</h3>

          <div class="tag-row">
            <span class="entity-tag primary">{{ displayType }}</span>
          </div>
        </div>
      </div>

      <div class="hero-stats">
        <div class="stat-box">
          <strong>{{ relatedNodes.length }}</strong>
          <span>关联节点</span>
        </div>
        <div class="stat-box">
          <strong>{{ relatedEdges.length }}</strong>
          <span>可视关系</span>
        </div>
        <div class="stat-box">
          <strong>{{ rawRelatedEdges.length }}</strong>
          <span>关系记录</span>
        </div>
        <div class="stat-box">
          <strong>{{ evidenceRows.length }}</strong>
          <span>证据条目</span>
        </div>
      </div>
    </header>

    <nav class="detail-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </nav>

    <main class="detail-body">
      <section v-show="activeTab === 'overview'" class="detail-section">
        <h4 class="section-title">基本信息</h4>

        <div class="info-list">
          <div v-for="row in primaryRows" :key="row.key" class="info-row">
            <div class="info-key">{{ row.label }}</div>
            <div class="info-value" :title="row.value">{{ row.value }}</div>
          </div>
        </div>

        <h4 class="section-title compact">标签</h4>
        <div class="tag-cloud">
          <span v-for="tag in normalizedLabels" :key="tag" class="pill">
            {{ tag }}
          </span>
          <span v-if="normalizedLabels.length === 0" class="empty-text unclassified">未分类</span>
        </div>

        <h4 class="section-title compact">关联概览</h4>
        <div class="relation-summary">
          <button type="button" class="summary-card" @click="activeTab = 'nodes'">
            <strong>{{ relatedNodes.length }}</strong>
            <em>关联节点</em>
          </button>

          <button type="button" class="summary-card" @click="activeTab = 'edges'">
            <strong>{{ relatedEdges.length }}</strong>
            <em>可视关系</em>
          </button>

          <button type="button" class="summary-card" @click="activeTab = 'edges'">
            <strong>{{ rawRelatedEdges.length }}</strong>
            <em>关系记录</em>
          </button>
        </div>
      </section>

      <section v-show="activeTab === 'properties'" class="detail-section">
        <h4 class="section-title">完整属性</h4>

        <div class="info-list">
          <div v-for="row in propertyDisplayRows" :key="row.key" class="info-row">
            <div class="info-key">{{ row.label }}</div>
            <div class="info-value" :title="row.value">{{ row.value }}</div>
          </div>
        </div>

        <div v-if="propertyRows.length === 0" class="empty-block">暂无可展示属性</div>
      </section>

      <section v-show="activeTab === 'nodes'" class="detail-section">
        <div class="section-head">
          <h4 class="section-title no-margin">关联节点</h4>
          <span class="section-count">{{ relatedNodes.length }}</span>
        </div>

        <div class="node-list">
          <div
            v-for="node in relatedNodes"
            :key="node.id"
            class="node-card"
            role="button"
            tabindex="0"
            @click="handleFocusNode(node)"
            @keydown.enter="handleFocusNode(node)"
          >
            <span class="mini-node-icon">{{ getNodeInitial(node) }}</span>
            <span class="node-main">
              <strong :title="getNodeTitle(node)">{{ getNodeTitle(node) }}</strong>
              <em>{{ getNodeType(node) }}</em>
            </span>
            <span class="jump-icon">定位</span>
          </div>
        </div>

        <div v-if="relatedNodes.length === 0" class="empty-block">暂无关联节点</div>
      </section>

      <section v-show="activeTab === 'edges'" class="detail-section">
        <div class="section-head">
          <h4 class="section-title no-margin">关联关系</h4>
          <span class="section-count">{{ relatedEdges.length }}</span>
        </div>

        <div class="edge-list">
          <div
            v-for="edge in relatedEdges"
            :key="getEdgeStableKey(edge)"
            class="edge-card"
            role="button"
            tabindex="0"
            @click="handleFocusEdge(edge)"
            @keydown.enter="handleFocusEdge(edge)"
          >
            <span class="edge-dot"></span>
            <span class="edge-main">
              <strong :title="getEdgeTitle(edge)">{{ getEdgeTitle(edge) }}</strong>
              <em>{{ getEdgeEndpointText(edge) }}</em>
            </span>
            <span class="jump-icon">高亮</span>
          </div>
        </div>

        <div v-if="relatedEdges.length === 0" class="empty-block">暂无关联关系</div>
      </section>

      <section v-show="activeTab === 'evidence'" class="detail-section">
        <div class="section-head">
          <h4 class="section-title no-margin">证据信息</h4>
          <span class="section-count">{{ evidenceRows.length }}</span>
        </div>

        <div class="evidence-list">
          <div v-for="row in evidenceRows" :key="row.key" class="evidence-card">
            <div class="evidence-title">{{ row.label }}</div>
            <div class="evidence-value" :title="row.value">{{ row.value }}</div>
          </div>
        </div>

        <div v-if="evidenceRows.length === 0" class="empty-block">暂无证据信息</div>
      </section>
    </main>

    <footer class="detail-actions">
      <button class="secondary-action" type="button" @click="copyCurrentId">复制节点 ID</button>
      <button class="primary-action" type="button" @click="exportCurrentDetail">
        导出节点信息
      </button>
    </footer>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { message } from 'ant-design-vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  item: {
    type: Object,
    default: null
  },
  type: {
    type: String,
    default: 'node'
  },
  nodes: {
    type: Array,
    default: () => []
  },
  edges: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close', 'focus-node', 'focus-edge'])

const activeTab = ref('overview')

const tabs = [
  { key: 'overview', label: '概览' },
  { key: 'properties', label: '属性' },
  { key: 'nodes', label: '关联节点' },
  { key: 'edges', label: '关联关系' },
  { key: 'evidence', label: '证据' }
]

const propertyLabelMap = {
  id: 'ID',
  name: '名称',
  title: '标题',
  label: '标签',
  type: '类型',
  entity_id: '实体ID',
  entity_type: '实体类型',
  display_type: '显示类型',
  description: '描述',
  kg_source: '数据来源',
  source_id: '来源片段',
  file_path: '来源文件',
  created_at: '创建时间',
  truncate: '截断标记',
  marker_type: '标记类型',
  evidence_type: '证据类型',
  confidence: '置信度',
  doi: 'DOI',
  year: '年份',
  statistic: '统计值',
  pvalue: 'P 值',
  qvalue: 'Q 值',
  population_size: '群体规模',
  validation_status: '验证状态'
}

const GENERIC_VALUES = new Set(['entity', 'upload', 'node', 'unknown', ''])

function getBusinessType(source) {
  if (!source || typeof source !== 'object') return '未分类'

  const layers = [source, source.data, source.properties]

  // Priority 1: display_type
  for (const layer of layers) {
    if (!layer || typeof layer !== 'object') continue
    if (layer.display_type && !GENERIC_VALUES.has(String(layer.display_type).toLowerCase())) {
      return String(layer.display_type)
    }
  }

  // Priority 2: entity_type
  for (const layer of layers) {
    if (!layer || typeof layer !== 'object') continue
    if (layer.entity_type && !GENERIC_VALUES.has(String(layer.entity_type).toLowerCase())) {
      return String(layer.entity_type)
    }
  }

  // Priority 3: non-generic Neo4j label
  for (const layer of layers) {
    if (!layer || typeof layer !== 'object') continue
    const labels = layer.labels
    if (Array.isArray(labels)) {
      for (const l of labels) {
        if (l && !GENERIC_VALUES.has(String(l).toLowerCase())) return String(l)
      }
    }
  }

  // Priority 4-5: type, category
  for (const layer of layers) {
    if (!layer || typeof layer !== 'object') continue
    if (layer.type && !GENERIC_VALUES.has(String(layer.type).toLowerCase())) {
      return String(layer.type)
    }
    if (layer.category && !GENERIC_VALUES.has(String(layer.category).toLowerCase())) {
      return String(layer.category)
    }
  }

  return '未分类'
}

watch(
  () => props.item,
  () => {
    activeTab.value = 'overview'
  }
)

const itemData = computed(() => props.item || {})

const itemPayload = computed(() => {
  return itemData.value?.data || itemData.value || {}
})

const original = computed(() => {
    const payload = itemPayload.value
    let raw = payload?.original || payload?.data?.original || payload || {}
    if (!raw || typeof raw !== 'object') return raw || {}

    // Walk nested properties chain so deeply buried fields (entity_type, etc.)
    // become accessible directly via original.value.<field>
    const merged = { ...raw }
    let cursor = raw
    for (let i = 0; i < 3 && cursor?.properties && typeof cursor.properties === 'object'; i++) {
      cursor = cursor.properties
      for (const [k, v] of Object.entries(cursor)) {
        if (v !== null && v !== undefined && typeof v !== 'object') {
          merged[k] = v
        }
      }
    }
    return merged
  })

const currentId = computed(() => {
  return String(itemData.value?.id || original.value?.id || itemPayload.value?.id || '')
})

const displayTitle = computed(() => {
  const data = original.value
  return (
    data.name ||
    data.title ||
    data.label ||
    itemPayload.value?.label ||
    itemData.value?.id ||
    '未命名节点'
  )
})

const displayType = computed(() => {
    if (props.type === 'edge') {
      const data = original.value
      const relationTypes = itemPayload.value?.relationTypes || []
      if (relationTypes.length > 0) return relationTypes.join(' / ')
      return data.type || data.label || itemPayload.value?.label || 'Relationship'
    }
    return getBusinessType(original.value)
  })

const panelTitle = computed(() => {
  return props.type === 'edge' ? '关系详情' : '节点详情'
})

const avatarText = computed(() => {
  const text = String(displayTitle.value || displayType.value || 'N')
  return text.slice(0, 1).toUpperCase()
})

const normalizedLabels = computed(() => {
    const bt = displayType.value
    return bt && bt !== '未分类' ? [bt] : []
  })

const propertyRows = computed(() => {
  const data = original.value || {}

  return Object.entries(data)
    .filter(([key, value]) => {
      return (
        value !== undefined &&
        value !== null &&
        value !== '' &&
        typeof value !== 'object' &&
        !['labels'].includes(key)
      )
    })
    .map(([key, value]) => ({
      key,
      label: propertyLabelMap[key] || key,
      value: String(value)
    }))
})

const primaryRows = computed(() => {
  const rows = []

  // ID
  const idRow = propertyRows.value.find((r) => r.key === 'id')
  if (idRow) rows.push(idRow)

  // 名称
  const nameRow = propertyRows.value.find((r) => r.key === 'name')
  if (nameRow) rows.push(nameRow)

  // 类型 (synthetic, single business type)
  rows.push({ key: '_type', label: '类型', value: displayType.value })

  // 描述
  const descRow = propertyRows.value.find((r) => r.key === 'description')
  if (descRow) rows.push(descRow)

  return rows
})

const PROP_IGNORE_KEYS = new Set(['graph_type', 'display_type', 'entity_type'])
const PROP_IGNORE_TYPE_VALUES = new Set(['entity', 'upload', 'node', 'unknown'])

const propertyDisplayRows = computed(() => {
  const rows = []

  // Synthetic type row (single business type)
  rows.push({ key: '_type', label: '类型', value: displayType.value })

  // Filter original property rows
  for (const row of propertyRows.value) {
    // Skip redundant type keys
    if (PROP_IGNORE_KEYS.has(row.key)) continue
    // Skip generic type values
    if (row.key === 'type' && PROP_IGNORE_TYPE_VALUES.has(String(row.value).toLowerCase())) continue
    rows.push(row)
  }

  return rows
})

function isEvidenceNode(node) {
  const text = [
    node?.display_type,
    node?.type,
    node?.evidence_type,
    node?.name,
    node?.title,
    node?.label
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()

  return (
    text.includes('evidence') ||
    text.includes('literature') ||
    text.includes('annotation') ||
    text.includes('transcriptomics') ||
    text.includes('metabolomics') ||
    text.includes('variant') ||
    text.includes('paper') ||
    text.includes('doi') ||
    text.includes('证据') ||
    text.includes('文献')
  )
}

function pickEvidenceFields(source, prefix = '') {
  const rows = []
  if (!source || typeof source !== 'object') return rows

  const keys = [
    'name',
    'title',
    'type',
    'label',
    'evidence_type',
    'confidence',
    'statistic',
    'score',
    'pvalue',
    'qvalue',
    'doi',
    'year',
    'kg_source',
    'source'
  ]

  for (const key of keys) {
    const value = source[key]
    if (value === undefined || value === null || value === '') continue

    rows.push({
      key: `${prefix}${key}`,
      label: `${prefix}${propertyLabelMap[key] || key}`,
      value: String(value)
    })
  }

  return rows
}

const evidenceRows = computed(() => {
  const rows = []

  // 1. 当前节点自身属性中的证据信息
  const selfEvidenceKeys = [
    'confidence',
    'score',
    'statistic',
    'pvalue',
    'qvalue',
    'doi',
    'source',
    'kg_source',
    'evidence',
    'year'
  ]

  for (const row of propertyRows.value) {
    const key = row.key.toLowerCase()
    if (selfEvidenceKeys.some((keyword) => key.includes(keyword))) {
      rows.push({
        key: `self-${row.key}`,
        label: row.label,
        value: row.value
      })
    }
  }

  // 2. 关联 Evidence / Paper 节点中的证据信息
  for (const node of relatedNodes.value) {
    if (!isEvidenceNode(node)) continue

    const nodeTitle = getNodeTitle(node)
    const pickedRows = pickEvidenceFields(node, `${nodeTitle} / `)

    if (pickedRows.length > 0) {
      rows.push(...pickedRows)
    } else {
      rows.push({
        key: `evidence-node-${node.id}`,
        label: '关联证据节点',
        value: nodeTitle
      })
    }
  }

  // 3. 关联边中的证据信息，包括 merged edge 的 originals
  for (const edge of rawRelatedEdges.value) {
    const relationName = edge.type || edge.label || edge.name || edge.data?.label || 'RELATED_TO'
    const pickedRows = pickEvidenceFields(edge, `${relationName} / `)

    if (pickedRows.length > 0) {
      rows.push(...pickedRows)
    }

    const originals = edge.data?.originals || edge.originals || []
    for (const [index, originalEdge] of originals.entries()) {
      rows.push(...pickEvidenceFields(originalEdge, `${relationName} 原始边${index + 1} / `))
    }
  }

  const seen = new Set()

  return rows.filter((row) => {
    const signature = `${row.label}::${row.value}`
    if (seen.has(signature)) return false
    seen.add(signature)
    return true
  })
})

const confidenceText = computed(() => {
  const confidence = original.value?.confidence || itemPayload.value?.confidence
  if (confidence === undefined || confidence === null || confidence === '') return '-'
  return String(confidence)
})

const rawRelatedEdges = computed(() => {
  const nodeId = currentId.value
  if (!nodeId) return []

  if (props.type === 'edge') {
    return [itemData.value].filter(Boolean)
  }

  return props.edges.filter((edge) => {
    const source = String(edge.source_id || edge.source || '')
    const target = String(edge.target_id || edge.target || '')
    return source === nodeId || target === nodeId
  })
})

const relatedEdges = computed(() => {
  const edgeMap = new Map()

  for (const edge of rawRelatedEdges.value) {
    const source = String(edge.source_id || edge.source || '')
    const target = String(edge.target_id || edge.target || '')

    if (!source || !target) continue

    const key = [source, target].sort().join('__')
    const relationType = edge.type || edge.label || edge.name || edge.data?.label || 'RELATED_TO'

    if (!edgeMap.has(key)) {
      edgeMap.set(key, {
        id: edge.id || `visual-edge-${edgeMap.size}`,
        source,
        target,
        relationTypes: [],
        relationCount: 0,
        originals: []
      })
    }

    const merged = edgeMap.get(key)

    if (!merged.relationTypes.includes(relationType)) {
      merged.relationTypes.push(relationType)
    }

    merged.relationCount += 1
    merged.originals.push(edge)
  }

  return Array.from(edgeMap.values())
})

const relatedNodes = computed(() => {
  const nodeId = currentId.value
  const nodeMap = new Map()

  for (const edge of rawRelatedEdges.value) {
    const source = String(edge.source_id || edge.source || '')
    const target = String(edge.target_id || edge.target || '')
    const otherId = source === nodeId ? target : source

    if (!otherId || otherId === nodeId || nodeMap.has(otherId)) continue

    const found = props.nodes.find((node) => String(node.id) === otherId)

    if (found) {
      nodeMap.set(otherId, found)
    } else {
      nodeMap.set(otherId, {
        id: otherId,
        name: otherId,
        display_type: 'Entity'
      })
    }
  }

  return Array.from(nodeMap.values())
})

const normalizedDetail = computed(() => {
  return {
    type: props.type,
    id: currentId.value,
    title: displayTitle.value,
    displayType: displayType.value,
    labels: normalizedLabels.value,
    properties: original.value,
    relatedNodes: relatedNodes.value,
    relatedEdges: relatedEdges.value
  }
})

function getNodeTitle(node) {
  return node?.name || node?.title || node?.label || node?.id || '未命名节点'
}

function getNodeType(node) {
  return getBusinessType(node)
}

function getNodeInitial(node) {
  return String(getNodeTitle(node)).slice(0, 1).toUpperCase()
}

function getEdgeStableKey(edge) {
  return String(edge.id || `${edge.source}-${edge.target}-${getEdgeTitle(edge)}`)
}

function getEdgeTitle(edge) {
  const relationTypes = edge?.relationTypes || edge?.data?.relationTypes || []
  if (relationTypes.length === 0) {
    return edge?.type || edge?.label || edge?.name || edge?.data?.label || 'RELATED_TO'
  }

  if (relationTypes.length === 1) return relationTypes[0]

  return `${relationTypes[0]} +${relationTypes.length - 1}`
}

function getEdgeEndpointText(edge) {
  const source = edge?.source_id || edge?.source || ''
  const target = edge?.target_id || edge?.target || ''
  const count = edge?.relationCount || edge?.originals?.length || 1

  if (!source && !target) return '暂无端点信息'

  return `${source} → ${target}${count > 1 ? `｜原始边 ${count} 条` : ''}`
}

function handleFocusEdge(edge) {
  emit('focus-edge', {
    id: edge.id,
    source: edge.source_id || edge.source,
    target: edge.target_id || edge.target,
    type: getEdgeTitle(edge)
  })
}

function handleFocusNode(node) {
  emit('focus-node', {
    id: node?.id,
    name: node?.name,
    title: node?.title,
    label: node?.label,
    originalId: node?.original?.id,
    raw: node
  })
}

async function copyText(text, successMessage) {
  const value = String(text || '')
  if (!value) {
    message.warning('没有可复制的内容')
    return
  }

  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(value)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = value
      textarea.setAttribute('readonly', '')
      textarea.style.position = 'fixed'
      textarea.style.top = '-9999px'
      textarea.style.left = '-9999px'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }

    message.success(successMessage)
  } catch (error) {
    console.error(error)
    message.error('复制失败，请手动复制')
  }
}

function copyCurrentId() {
  copyText(currentId.value, '节点 ID 已复制')
}

function exportCurrentDetail() {
  copyText(JSON.stringify(normalizedDetail.value, null, 2), '节点详情已复制到剪贴板')
}
</script>

<style lang="less" scoped>
.kg-detail-card {
  width: 100%;
  height: 100%;
  min-height: 0;
  background: #ffffff;
  border: 1px solid #dbeafe;
  border-radius: 18px;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.16);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  user-select: text;
}

.kg-detail-card * {
  user-select: text;
}

button,
.close-btn,
.tab-btn,
.summary-card,
.primary-action,
.secondary-action {
  user-select: none;
}

.entity-title,
.info-key,
.info-value,
.evidence-title,
.evidence-value,
.node-main strong,
.node-main em,
.edge-main strong,
.edge-main em,
.pill,
.entity-tag {
  user-select: text;
}

.kg-detail-hero {
  position: relative;
  padding: 22px 20px 16px;
  color: #ffffff;
  background:
    radial-gradient(circle at 20% 0%, rgba(255, 255, 255, 0.38), transparent 28%),
    linear-gradient(135deg, #1677ff 0%, #5b5df5 48%, #7c3aed 100%);
}

.close-btn {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 20;
  width: 26px;
  height: 26px;
  border: none;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.96);
  background: rgba(255, 255, 255, 0.14);
  cursor: pointer;
  padding: 0;
  pointer-events: auto;
}

.close-btn span {
  display: block;
  font-size: 18px;
  line-height: 1;
  transform: translateY(-1px);
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.26);
}

.hero-main {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding-right: 36px;
}

.avatar {
  width: 48px;
  height: 48px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.86);
  color: #1677ff;
  font-size: 22px;
  font-weight: 800;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.18);
}

.hero-text {
  min-width: 0;
  flex: 1;
}

.eyebrow {
  font-size: 12px;
  font-weight: 700;
  opacity: 0.9;
  margin-bottom: 4px;
}

.entity-title {
  margin: 0;
  font-size: 18px;
  line-height: 1.35;
  font-weight: 800;
  max-width: 100%;
  white-space: normal;
  overflow: visible;
  text-overflow: unset;
  word-break: break-word;
}

.tag-row {
  margin-top: 9px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.entity-tag {
  max-width: 120px;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  line-height: 1.2;
  color: #eef6ff;
  background: rgba(255, 255, 255, 0.18);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entity-tag.primary {
  background: rgba(255, 255, 255, 0.28);
  font-weight: 700;
}

.hero-stats {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.stat-box {
  padding: 8px 6px;
  border-radius: 12px;
  text-align: center;
  background: rgba(255, 255, 255, 0.12);
}

.stat-box strong {
  display: block;
  font-size: 17px;
  line-height: 1.2;
}

.stat-box span {
  display: block;
  margin-top: 3px;
  font-size: 11px;
  opacity: 0.86;
  white-space: nowrap;
}

.detail-tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0 14px;
  height: 46px;
  border-bottom: 1px solid #e5e7eb;
  background: #ffffff;
}

.tab-btn {
  height: 46px;
  padding: 0 8px;
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
}

.tab-btn.active {
  color: #1677ff;
  border-bottom-color: #1677ff;
}

.detail-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 18px 20px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.detail-section {
  min-height: 100%;
}

.section-title {
  margin: 0 0 10px;
  color: #0f172a;
  font-size: 14px;
  font-weight: 800;
}

.section-title.compact {
  margin-top: 18px;
}

.section-title.no-margin {
  margin: 0;
}

.section-head {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-count {
  min-width: 24px;
  height: 22px;
  border-radius: 999px;
  display: inline-grid;
  place-items: center;
  padding: 0 7px;
  font-size: 12px;
  color: #0958d9;
  background: #e6f4ff;
  border: 1px solid #bfdbfe;
}

.info-list {
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  overflow: hidden;
  background: #ffffff;
}

.info-row {
  display: grid;
  grid-template-columns: 94px minmax(0, 1fr);
  border-bottom: 1px solid #eef2f7;
}

.info-row:last-child {
  border-bottom: none;
}

.info-key {
  padding: 10px 10px;
  background: #f8fafc;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  border-right: 1px solid #eef2f7;
}

.info-value {
  padding: 10px 10px;
  color: #1e293b;
  font-size: 12px;
  line-height: 1.5;
  word-break: break-word;
  overflow-wrap: anywhere;
  white-space: normal;
  user-select: text;
}

.tag-cloud {
  min-height: 42px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: auto;
  max-width: 100%;
  padding: 6px 12px;
  line-height: 1;
  border-radius: 999px;
  white-space: nowrap;
  color: #0958d9;
  border: 1px solid #bfdbfe;
  background: #e6f4ff;
  font-size: 12px;
  font-weight: 600;
}

.empty-text.unclassified {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 11px;
  color: #94a3b8;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
}

.relation-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.summary-card {
  border: 1px solid #e5e7eb;
  background: #ffffff;
  border-radius: 14px;
  padding: 10px 6px;
  cursor: pointer;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.summary-card:hover {
  border-color: #91caff;
  background: #f0f7ff;
}

.summary-card strong {
  display: block;
  color: #0f172a;
  font-size: 17px;
  line-height: 1.2;
}

.summary-card em {
  display: block;
  color: #64748b;
  font-style: normal;
  font-size: 10px;
  white-space: nowrap;
}

.node-list,
.edge-list,
.evidence-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.node-card,
.edge-card {
  width: 100%;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  border-radius: 14px;
  padding: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 9px;
  text-align: left;
  cursor: pointer;
  user-select: text;
}

.node-card:hover,
.edge-card:hover {
  border-color: #91caff;
  background: #f0f7ff;
}

.mini-node-icon {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: #e6f4ff;
  border: 1px solid #91caff;
  color: #1677ff;
  font-size: 12px;
  font-weight: 800;
}

.node-main,
.edge-main {
  flex: 1;
  min-width: 0;
}

.node-main strong,
.edge-main strong {
  display: block;
  color: #0f172a;
  font-size: 13px;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-main em,
.edge-main em {
  display: block;
  margin-top: 3px;
  color: #64748b;
  font-size: 11px;
  font-style: normal;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.jump-icon {
  flex-shrink: 0;
  color: #1677ff;
  font-size: 12px;
  font-weight: 700;
}

.edge-dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: #1677ff;
  box-shadow: 0 0 0 4px #e6f4ff;
  flex-shrink: 0;
}

.evidence-card {
  border: 1px solid #e5e7eb;
  background: #ffffff;
  border-radius: 14px;
  padding: 11px 12px;
}

.evidence-title {
  color: #0f172a;
  font-size: 13px;
  font-weight: 700;
}

.evidence-value {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
  word-break: break-word;
}

.empty-block {
  padding: 28px 12px;
  border: 1px dashed #cbd5e1;
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.7);
  color: #94a3b8;
  text-align: center;
}

.empty-text {
  color: #94a3b8;
  font-size: 12px;
}

.detail-actions {
  flex-shrink: 0;
  padding: 12px 16px 16px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  border-top: 1px solid #e5e7eb;
  background: #ffffff;
}

.primary-action,
.secondary-action {
  height: 36px;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 700;
  font-size: 13px;
}

.primary-action {
  border: none;
  color: #ffffff;
  background: linear-gradient(135deg, #1677ff 0%, #7c3aed 100%);
  box-shadow: 0 10px 20px rgba(22, 119, 255, 0.18);
}

.secondary-action {
  color: #1677ff;
  border: 1px solid #bfdbfe;
  background: #ffffff;
}

.primary-action:hover,
.secondary-action:hover {
  transform: translateY(-1px);
}
</style>
