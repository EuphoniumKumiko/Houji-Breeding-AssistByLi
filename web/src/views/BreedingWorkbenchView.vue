<template>
  <div class="breeding-workbench-page">
    <div class="workbench-body">
      <section class="config-panel">
        <div class="panel-intro">
          <h2>输入配置</h2>
          <p>左侧维护可编辑的组学输入配置；第一版不上传文件到后端，只把文件名和字段上下文发给智能体。</p>
        </div>

        <a-collapse v-model:activeKey="activePanels" ghost class="breeding-collapse">
          <a-collapse-panel key="reference" header="参考基因组">
            <div class="field-grid single-column-grid">
              <div class="field-item">
                <label class="field-label">参考基因组</label>
                <div
                  class="file-input-row"
                  :class="{ dragging: dragState.reference_genome }"
                  @dragover.prevent="dragState.reference_genome = true"
                  @dragleave.prevent="dragState.reference_genome = false"
                  @drop.prevent="handleFileDrop('reference_genome', $event)"
                >
                  <div class="file-input-control">
                    <a-input v-model:value="form.reference_genome" :disabled="running" />
                    <a-button size="small" :disabled="running" @click="openFilePicker('reference_genome')">
                      添加文件
                    </a-button>
                  </div>
                  <input
                    :ref="(el) => registerFileInput('reference_genome', el)"
                    class="hidden-file-input"
                    type="file"
                    @change="handleSingleFileChange('reference_genome', $event)"
                  />
                </div>
              </div>

              <div class="field-item">
                <label class="field-label">基因组注释</label>
                <div
                  class="file-input-row"
                  :class="{ dragging: dragState.genome_gff }"
                  @dragover.prevent="dragState.genome_gff = true"
                  @dragleave.prevent="dragState.genome_gff = false"
                  @drop.prevent="handleFileDrop('genome_gff', $event)"
                >
                  <div class="file-input-control">
                    <a-input v-model:value="form.genome_gff" :disabled="running" />
                    <a-button size="small" :disabled="running" @click="openFilePicker('genome_gff')">
                      添加文件
                    </a-button>
                  </div>
                  <input
                    :ref="(el) => registerFileInput('genome_gff', el)"
                    class="hidden-file-input"
                    type="file"
                    @change="handleSingleFileChange('genome_gff', $event)"
                  />
                </div>
              </div>

              <div class="field-item">
                <label class="field-label">基因功能注释</label>
                <div
                  class="file-input-row"
                  :class="{ dragging: dragState.function_annotation }"
                  @dragover.prevent="dragState.function_annotation = true"
                  @dragleave.prevent="dragState.function_annotation = false"
                  @drop.prevent="handleFileDrop('function_annotation', $event)"
                >
                  <div class="file-input-control">
                    <a-input v-model:value="form.function_annotation" :disabled="running" />
                    <a-button size="small" :disabled="running" @click="openFilePicker('function_annotation')">
                      添加文件
                    </a-button>
                  </div>
                  <input
                    :ref="(el) => registerFileInput('function_annotation', el)"
                    class="hidden-file-input"
                    type="file"
                    @change="handleSingleFileChange('function_annotation', $event)"
                  />
                </div>
              </div>
            </div>
            <p class="hint-text">输出说明：无输出</p>
          </a-collapse-panel>

          <a-collapse-panel key="transcriptome" header="转录组">
            <div class="field-grid single-column-grid">
              <div class="field-item">
                <label class="field-label">RNA-seq Reads</label>
                <div
                  class="file-input-row"
                  :class="{ dragging: dragState.rnaseq_reads }"
                  @dragover.prevent="dragState.rnaseq_reads = true"
                  @dragleave.prevent="dragState.rnaseq_reads = false"
                  @drop.prevent="handleFileDrop('rnaseq_reads', $event, true)"
                >
                  <div class="file-input-control">
                    <a-input v-model:value="form.rnaseq_reads" :disabled="running" />
                    <a-button size="small" :disabled="running" @click="openFilePicker('rnaseq_reads')">
                      添加文件
                    </a-button>
                  </div>
                  <input
                    :ref="(el) => registerFileInput('rnaseq_reads', el)"
                    class="hidden-file-input"
                    type="file"
                    multiple
                    accept=".fq,.fastq,.gz"
                    @change="handleMultiFileChange('rnaseq_reads', $event)"
                  />
                </div>
                <div v-if="selectedFiles.rnaseq_reads.length" class="file-chip-list">
                  <span v-for="item in selectedFiles.rnaseq_reads" :key="item.name" class="file-chip">
                    {{ item.name }}
                  </span>
                </div>
              </div>

              <div class="field-item">
                <label class="field-label">数据标签</label>
                <div
                  class="file-input-row"
                  :class="{ dragging: dragState.sample_map }"
                  @dragover.prevent="dragState.sample_map = true"
                  @dragleave.prevent="dragState.sample_map = false"
                  @drop.prevent="handleFileDrop('sample_map', $event)"
                >
                  <div class="file-input-control">
                    <a-input v-model:value="form.sample_map" :disabled="running" />
                    <a-button size="small" :disabled="running" @click="openFilePicker('sample_map')">
                      添加文件
                    </a-button>
                  </div>
                  <input
                    :ref="(el) => registerFileInput('sample_map', el)"
                    class="hidden-file-input"
                    type="file"
                    @change="handleSingleFileChange('sample_map', $event)"
                  />
                </div>
              </div>

              <div class="field-item">
                <label class="field-label">流程说明</label>
                <div
                  class="file-input-row"
                  :class="{ dragging: dragState.usage_doc }"
                  @dragover.prevent="dragState.usage_doc = true"
                  @dragleave.prevent="dragState.usage_doc = false"
                  @drop.prevent="handleFileDrop('usage_doc', $event)"
                >
                  <div class="file-input-control">
                    <a-input v-model:value="form.usage_doc" :disabled="running" />
                    <a-button size="small" :disabled="running" @click="openFilePicker('usage_doc')">
                      添加文件
                    </a-button>
                  </div>
                  <input
                    :ref="(el) => registerFileInput('usage_doc', el)"
                    class="hidden-file-input"
                    type="file"
                    @change="handleSingleFileChange('usage_doc', $event)"
                  />
                </div>
              </div>
            </div>
            <p class="hint-text">输出：差异显著基因 <code>significant_de_genes.tsv</code></p>
          </a-collapse-panel>

          <a-collapse-panel key="metabolome" header="代谢组">
            <div class="field-grid single-column-grid">
              <div class="field-item">
                <label class="field-label">代谢含量</label>
                <div
                  class="file-input-row"
                  :class="{ dragging: dragState.metabolome_tsv }"
                  @dragover.prevent="dragState.metabolome_tsv = true"
                  @dragleave.prevent="dragState.metabolome_tsv = false"
                  @drop.prevent="handleFileDrop('metabolome_tsv', $event)"
                >
                  <div class="file-input-control">
                    <a-input v-model:value="form.metabolome_tsv" :disabled="running" />
                    <a-button size="small" :disabled="running" @click="openFilePicker('metabolome_tsv')">
                      添加文件
                    </a-button>
                  </div>
                  <input
                    :ref="(el) => registerFileInput('metabolome_tsv', el)"
                    class="hidden-file-input"
                    type="file"
                    @change="handleSingleFileChange('metabolome_tsv', $event)"
                  />
                </div>
              </div>
            </div>
            <p class="hint-text">输出说明：无输出</p>
          </a-collapse-panel>

          <a-collapse-panel key="trait" header="性状输入">
            <div class="field-grid">
              <div class="field-item full-width">
                <label class="field-label">性状输入</label>
                <a-input
                  v-model:value="form.trait"
                  size="large"
                  placeholder="请输入性状描述"
                  :disabled="running"
                />
              </div>
            </div>
            <p class="hint-text">这里是性状描述，不是文件上传，也不是标签选择。</p>
          </a-collapse-panel>

          <a-collapse-panel key="question" header="用户问题">
            <div class="field-grid">
              <div class="field-item full-width">
                <label class="field-label">用户问题</label>
                <a-textarea
                  v-model:value="form.user_question"
                  :rows="5"
                  :disabled="running"
                  placeholder="请输入你的育种问题，例如：给出一些育种建议"
                />
              </div>
            </div>
            <p class="hint-text">
              智能体会根据性状输入和多组学数据自动选择工具，并按育种建议规范生成答案。
            </p>

            <div class="action-row">
              <a-button type="primary" size="large" :loading="running" @click="handleSubmit">
                提交给智能体
              </a-button>
              <a-button size="large" :disabled="running" @click="handleReset">重置</a-button>
            </div>
          </a-collapse-panel>
        </a-collapse>
      </section>

      <section class="result-panel">
        <div class="panel-intro result-header">
          <div>
            <h2>智能体输出 / 育种建议</h2>
            <p>以下结果由智能体根据用户问题、性状输入和多组学证据生成，并经过守卫规则检查。</p>
          </div>
        </div>

        <div class="chain-card">
          <div class="chain-card-top">
            <div class="chain-title">工具调用链</div>
            <div v-if="displayStatus" class="inline-status">
              <span class="status-label">状态</span>
              <span class="status-pill" :class="`status-${displayStatus.tone}`">
                {{ displayStatus.label }}
              </span>
            </div>
          </div>
          <div v-if="result.toolName || result.guardPassed !== null" class="chain-meta">
            <span v-if="result.toolName">tool: {{ result.toolName }}</span>
            <span v-if="result.guardPassed !== null">
              guard: {{ result.guardPassed ? 'passed' : 'failed' }}
            </span>
          </div>
          <div v-if="showSoftTimeoutActions" class="soft-timeout-actions">
            <div class="soft-timeout-text">
              智能体仍在执行，可能是模型或工具调用较慢。你可以继续等待或停止本次运行。
            </div>
            <div class="soft-timeout-buttons">
              <a-button type="primary" size="small" @click="handleContinueWaiting">继续等待</a-button>
              <a-button size="small" danger @click="handleStopRun">停止本次运行</a-button>
            </div>
          </div>
          <div v-if="visibleToolChain.length" class="chain-list">
            <span
              v-for="item in visibleToolChain"
              :key="item.name"
              class="chain-chip"
            >
              {{ item.label }}
            </span>
          </div>
          <div v-else class="result-block-body">
            {{ running ? '等待智能体调用工具' : '暂无工具调用记录' }}
          </div>
        </div>

        <a-alert
          v-if="errorMessage"
          type="error"
          show-icon
          :message="errorMessage"
          class="result-alert"
        />
        <a-alert
          v-else-if="!running && result.markdown && !compliancePassed"
          type="warning"
          show-icon
          :message="resultWarningMessage"
          class="result-alert"
        />

        <div class="result-shell">
          <a-spin :spinning="running && !softTimeoutState.awaitingDecision" :tip="spinTip">
            <template v-if="result.markdown">
              <div class="result-block-grid">
                <div class="result-block compliance-card">
                  <div class="result-block-title">合规检查</div>
                  <div class="compliance-list">
                    <div
                      v-for="item in complianceChecks"
                      :key="item.key"
                      class="compliance-item"
                    >
                      <span class="compliance-label">{{ item.label }}</span>
                      <span
                        class="compliance-badge"
                        :class="item.passed ? 'passed' : 'missing'"
                      >
                        <span class="status-dot"></span>
                        {{ item.passed ? '通过' : '缺失' }}
                      </span>
                    </div>
                  </div>
                </div>

                <div class="result-block literature-card">
                  <div class="result-block-title">文献 DOI 与引用原文</div>
                  <div v-if="literatureCards.length" class="literature-list">
                    <div
                      v-for="(item, index) in literatureCards"
                      :key="`${item.doi}-${index}`"
                      class="literature-item"
                    >
                      <div class="literature-doi">{{ item.doi }}</div>
                      <div v-if="item.title" class="literature-title">{{ item.title }}</div>
                      <div class="literature-quote">{{ item.quote }}</div>
                    </div>
                  </div>
                  <div v-else class="result-block-body">
                    当前智能体输出中未解析到 DOI 与引用原文。
                  </div>
                </div>

                <div class="result-block downloads-card">
                  <div class="result-block-title">下游可复用结果</div>
                  <div class="download-list">
                    <button type="button" class="download-card" @click="downloadSignificantDeg">
                      <span class="download-name">significant_de_genes.tsv</span>
                      <span class="download-desc">下载差异显著基因结果</span>
                    </button>
                    <button type="button" class="download-card" @click="downloadMetabolome">
                      <span class="download-name">metabolome_raw_3372.tsv</span>
                      <span class="download-desc">下载代谢组占位结果</span>
                    </button>
                    <button
                      type="button"
                      class="download-card"
                      :disabled="!result.markdown"
                      @click="downloadAdviceMarkdown"
                    >
                      <span class="download-name">育种建议</span>
                      <span class="download-desc">下载当前 breeding_advice.md</span>
                    </button>
                  </div>
                </div>
              </div>

              <div class="markdown-card">
                <MarkdownPreview :content="result.markdown" />
              </div>

              <div class="markdown-download-footer">
                <a-button
                  type="primary"
                  size="large"
                  :disabled="!result.markdown"
                  @click="downloadAdviceMarkdown"
                >
                  下载育种建议 Markdown
                </a-button>
              </div>

            </template>
            <a-empty
              v-else
              description="提交问题后，这里会显示由后端 Tool / Agent 生成的育种建议结果。"
            />

            <a-collapse v-if="hasDiagnostics" ghost class="diagnostic-collapse">
              <a-collapse-panel key="diagnostics" header="运行诊断信息">
                <div class="diagnostic-grid">
                  <div class="diagnostic-item"><span>thread_id</span><code>{{ runDiagnostics.threadId || '-' }}</code></div>
                  <div class="diagnostic-item"><span>run_id</span><code>{{ runDiagnostics.runId || '-' }}</code></div>
                  <div class="diagnostic-item"><span>run_status</span><code>{{ runDiagnostics.runStatus || '-' }}</code></div>
                  <div class="diagnostic-item"><span>elapsed_seconds</span><code>{{ runDiagnostics.elapsedSeconds }}</code></div>
                  <div class="diagnostic-item"><span>polling_count</span><code>{{ runDiagnostics.pollingCount }}</code></div>
                  <div class="diagnostic-item"><span>last_history_message_role</span><code>{{ runDiagnostics.lastHistoryMessageRole || '-' }}</code></div>
                  <div class="diagnostic-item"><span>parsed_tool_calls</span><code>{{ diagnosticsToolCalls }}</code></div>
                  <div class="diagnostic-item"><span>compliance_missing_items</span><code>{{ diagnosticsMissingItems }}</code></div>
                  <div class="diagnostic-item"><span>soft_timeout_reached</span><code>{{ String(runDiagnostics.softTimeoutReached) }}</code></div>
                  <div class="diagnostic-item"><span>hard_timeout_reached</span><code>{{ String(runDiagnostics.hardTimeoutReached) }}</code></div>
                </div>
              </a-collapse-panel>
            </a-collapse>
          </a-spin>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { storeToRefs } from 'pinia'
import { breedingWorkbenchApi } from '@/apis'
import MarkdownPreview from '@/components/common/MarkdownPreview.vue'
import { useAgentStore } from '@/stores/agent'
import {
  DEFAULT_SMOKE_BREEDING_CONTEXT,
  REQUIRED_BREEDING_FIELDS,
  downloadMarkdown,
  downloadTsv,
  evaluateBreedingCompliance,
  extractLiteratureEvidence
} from '@/utils/breedingWorkbench'

const DEFAULT_FORM = { ...DEFAULT_SMOKE_BREEDING_CONTEXT }
const DEFAULT_DATA_DIR = DEFAULT_SMOKE_BREEDING_CONTEXT.data_dir
const DEFAULT_TRAIT = DEFAULT_SMOKE_BREEDING_CONTEXT.trait
const DEFAULT_QUESTION = DEFAULT_SMOKE_BREEDING_CONTEXT.user_question
const TOOL_LABELS = {
  smoke_flavonoid_breeding_advice: 'Smoke 黄酮育种建议',
  breeding_reference_prepare: '参考基因组准备',
  breeding_transcriptome_deg: '转录组差异分析',
  breeding_metabolome_prepare: '代谢组准备',
  breeding_literature_evidence: '文献证据读取',
  breeding_advice_generate: '育种建议生成',
  breeding_validation_plan: '验证计划生成'
}
const INFERRED_LABEL_SUFFIX = '（文本推断）'

const agentStore = useAgentStore()
const { selectedAgentId, selectedAgentConfigId } = storeToRefs(agentStore)

const form = reactive({ ...DEFAULT_FORM })
const activePanels = ref(['reference', 'transcriptome', 'metabolome', 'trait', 'question'])
const running = ref(false)
const currentMode = ref('')
const errorMessage = ref('')
const softTimeoutDecisionResolver = ref(null)
const result = reactive({
  status: 'idle',
  markdown: '',
  toolCalls: [],
  toolChain: [],
  toolName: '',
  guardPassed: null,
  outputFiles: []
})
const runDiagnostics = reactive({
  threadId: '',
  runId: '',
  runStatus: '',
  elapsedSeconds: 0,
  pollingCount: 0,
  lastHistoryMessageRole: '',
  parsedToolCalls: [],
  softTimeoutReached: false,
  hardTimeoutReached: false
})
const softTimeoutState = reactive({
  reached: false,
  awaitingDecision: false,
  hardReached: false
})

const selectedFiles = reactive({
  reference_genome: [],
  genome_gff: [],
  function_annotation: [],
  rnaseq_reads: [],
  sample_map: [],
  usage_doc: [],
  metabolome_tsv: []
})

const dragState = reactive({
  reference_genome: false,
  genome_gff: false,
  function_annotation: false,
  rnaseq_reads: false,
  sample_map: false,
  usage_doc: false,
  metabolome_tsv: false
})

const fileInputRefs = new Map()

const displayStatus = computed(() => {
  if (running.value) {
    if (softTimeoutState.awaitingDecision) {
      return {
        label: '智能体仍在执行，可能是模型或工具调用较慢。你可以继续等待或停止本次运行。',
        tone: 'running'
      }
    }
    if (currentMode.value === 'repair') {
      return softTimeoutState.reached
        ? { label: '智能体仍在执行，可能是模型或工具调用较慢。你可以继续等待或停止本次运行。', tone: 'running' }
        : { label: '智能体正在根据合规检查重新整理结果...', tone: 'running' }
    }
    if (result.markdown) {
      return { label: '已获取智能体中间输出，等待任务结束确认...', tone: 'running' }
    }
    return { label: '智能体正在分析并调用工具，请稍候', tone: 'running' }
  }
  if (!result.status || result.status === 'idle') return null
  if (['completed', 'completed_with_warnings', 'succeeded'].includes(result.status)) {
    return {
      label: compliancePassed.value ? '智能体执行完成，合规检查通过' : '智能体执行完成',
      tone: 'success'
    }
  }
  if (softTimeoutState.hardReached) {
    return { label: '智能体执行时间过长，请检查后端 run 状态或重试', tone: 'failed' }
  }
  if (['failed', 'cancelled', 'interrupted', 'error'].includes(result.status)) {
    return { label: result.status, tone: 'failed' }
  }
  return null
})

const visibleToolChain = computed(() => {
  return (result.toolChain || []).map((item) => ({
    name: item.name,
    label: `${TOOL_LABELS[item.name] || item.name}${item.inferred ? INFERRED_LABEL_SUFFIX : ''}`
  }))
})

const complianceChecks = computed(() => evaluateBreedingCompliance(result.markdown || ''))

const compliancePassed = computed(() => complianceChecks.value.every((item) => item.passed))
const missingComplianceLabels = computed(() =>
  complianceChecks.value.filter((item) => !item.passed).map((item) => item.label)
)
const resultWarningMessage = computed(() =>
  missingComplianceLabels.value.length
    ? `输出仍未满足学长要求，缺失项：${missingComplianceLabels.value.join('、')}`
    : '输出未满足学长要求，请检查 Tool 返回或重新运行。'
)
const spinTip = computed(() =>
  currentMode.value === 'repair'
    ? '智能体正在根据合规检查重新整理结果...'
    : '智能体正在分析并调用工具，请稍候...'
)
const showSoftTimeoutActions = computed(() => running.value && softTimeoutState.awaitingDecision)
const hasDiagnostics = computed(
  () => !!(runDiagnostics.threadId || runDiagnostics.runId || runDiagnostics.pollingCount || result.markdown)
)
const diagnosticsToolCalls = computed(() =>
  runDiagnostics.parsedToolCalls.length ? runDiagnostics.parsedToolCalls.join(', ') : '-'
)
const diagnosticsMissingItems = computed(() =>
  missingComplianceLabels.value.length ? missingComplianceLabels.value.join('、') : '无'
)

const literatureCards = computed(() => {
  return extractLiteratureEvidence(result.markdown || '')
})

const registerFileInput = (key, el) => {
  if (el) {
    fileInputRefs.set(key, el)
  } else {
    fileInputRefs.delete(key)
  }
}

const openFilePicker = (key) => {
  fileInputRefs.get(key)?.click()
}

const updateFieldFiles = (key, files, multiple = false) => {
  const normalizedFiles = Array.from(files || []).map((file) => ({
    name: file.name,
    size: file.size,
    type: file.type
  }))
  selectedFiles[key] = normalizedFiles
  dragState[key] = false

  if (multiple) {
    form[key] = normalizedFiles.length > 0 ? normalizedFiles.map((file) => file.name).join(', ') : ''
  } else if (normalizedFiles[0]) {
    form[key] = normalizedFiles[0].name
  }
}

const handleSingleFileChange = (key, event) => {
  updateFieldFiles(key, event?.target?.files || [], false)
  if (event?.target) event.target.value = ''
}

const handleMultiFileChange = (key, event) => {
  updateFieldFiles(key, event?.target?.files || [], true)
  if (event?.target) event.target.value = ''
}

const handleFileDrop = (key, event, multiple = false) => {
  updateFieldFiles(key, event?.dataTransfer?.files || [], multiple)
}

const resetResult = () => {
  result.status = 'idle'
  result.markdown = ''
  result.toolCalls = []
  result.toolChain = []
  result.toolName = ''
  result.guardPassed = null
  result.outputFiles = []
  currentMode.value = ''
  runDiagnostics.threadId = ''
  runDiagnostics.runId = ''
  runDiagnostics.runStatus = ''
  runDiagnostics.elapsedSeconds = 0
  runDiagnostics.pollingCount = 0
  runDiagnostics.lastHistoryMessageRole = ''
  runDiagnostics.parsedToolCalls = []
  runDiagnostics.softTimeoutReached = false
  runDiagnostics.hardTimeoutReached = false
  softTimeoutState.reached = false
  softTimeoutState.awaitingDecision = false
  softTimeoutState.hardReached = false
  softTimeoutDecisionResolver.value = null
}

const resetFileSelections = () => {
  Object.keys(selectedFiles).forEach((key) => {
    selectedFiles[key] = []
  })
  Object.keys(dragState).forEach((key) => {
    dragState[key] = false
  })
}

const handleReset = () => {
  Object.assign(form, DEFAULT_FORM)
  errorMessage.value = ''
  resetResult()
  resetFileSelections()
}

const ensureAgentContext = async () => {
  if (!agentStore.isInitialized) {
    await agentStore.initialize()
  }
  if (!selectedAgentId.value || !selectedAgentConfigId.value) {
    throw new Error('当前没有可用的默认智能体或默认配置，请先在对话页或模型配置中确认。')
  }
}

const buildVisibleQuestion = () => {
  const question = (form.user_question || DEFAULT_QUESTION).trim()
  return question || DEFAULT_QUESTION
}

const buildTrait = () => {
  const trait = (form.trait || DEFAULT_TRAIT).trim()
  return trait || DEFAULT_TRAIT
}

const buildSubmissionContext = () => ({
  data_dir: DEFAULT_DATA_DIR,
  reference_genome: (form.reference_genome || '').trim() || DEFAULT_FORM.reference_genome,
  genome_gff: (form.genome_gff || '').trim() || DEFAULT_FORM.genome_gff,
  function_annotation: (form.function_annotation || '').trim() || DEFAULT_FORM.function_annotation,
  rnaseq_reads: (form.rnaseq_reads || '').trim() || DEFAULT_FORM.rnaseq_reads,
  sample_map: (form.sample_map || '').trim() || DEFAULT_FORM.sample_map,
  usage_doc: (form.usage_doc || '').trim() || DEFAULT_FORM.usage_doc,
  metabolome_tsv: (form.metabolome_tsv || '').trim() || DEFAULT_FORM.metabolome_tsv
})

const validateRequiredFields = () => {
  const missing = REQUIRED_BREEDING_FIELDS.find(({ key }) => !(form[key] || '').trim())
  if (!missing) return null
  return `${missing.label}不能为空，请补充后再提交。`
}

const downloadSignificantDeg = () => {
  const content = ['gene_id\tstatus', 'Si9g037800\tdetected'].join('\n')
  downloadTsv('significant_de_genes.tsv', content)
}

const downloadMetabolome = () => {
  const content = ['compound\tannotation', 'flavonoid_background\tmetabolome_raw_3372.tsv'].join('\n')
  downloadTsv('metabolome_raw_3372.tsv', content)
}

const downloadAdviceMarkdown = () => {
  if (!result.markdown) {
    message.warning('请先提交给智能体生成结果。')
    return
  }
  downloadMarkdown('breeding_advice.md', result.markdown)
}

const syncDiagnostics = (diagnostics = {}) => {
  runDiagnostics.threadId = diagnostics.threadId || ''
  runDiagnostics.runId = diagnostics.runId || ''
  runDiagnostics.runStatus = diagnostics.runStatus || ''
  runDiagnostics.elapsedSeconds = diagnostics.elapsedSeconds || 0
  runDiagnostics.pollingCount = diagnostics.pollingCount || 0
  runDiagnostics.lastHistoryMessageRole = diagnostics.lastHistoryMessageRole || ''
  runDiagnostics.parsedToolCalls = diagnostics.parsedToolCalls || []
  runDiagnostics.softTimeoutReached = Boolean(diagnostics.softTimeoutReached)
  runDiagnostics.hardTimeoutReached = Boolean(diagnostics.hardTimeoutReached)
  softTimeoutState.reached = Boolean(diagnostics.softTimeoutReached)
  softTimeoutState.hardReached = Boolean(diagnostics.hardTimeoutReached)
}

const syncResultFromPayload = (payload, { final = false } = {}) => {
  result.status = payload.status || (final ? 'completed' : result.status || 'running')
  result.markdown = payload.markdown || result.markdown || ''
  result.toolCalls = payload.toolCalls || result.toolCalls || []
  result.toolChain = payload.toolChain || result.toolChain || []
  result.toolName = payload.toolName || (payload.toolChain?.length === 1 ? payload.toolChain[0]?.name || '' : '')
  result.guardPassed = payload.guardPassed ?? result.guardPassed
  result.outputFiles = payload.outputFiles || result.outputFiles || []
  syncDiagnostics(payload.diagnostics || {})

  if (final && !result.markdown) {
    errorMessage.value = '后端运行已结束，但没有返回可渲染的结果内容。'
  }
}

const buildRepairPayload = (threadId, context, missingLabels) =>
  breedingWorkbenchApi.runBreedingWorkbench({
    agentId: selectedAgentId.value,
    agentConfigId: selectedAgentConfigId.value,
    trait: buildTrait(),
    question: buildVisibleQuestion(),
    context,
    threadId,
    queryOverride: breedingWorkbenchApi.buildRepairQuery(missingLabels),
    normalWaitMs: breedingWorkbenchApi.NORMAL_WAIT_MS,
    hardTimeoutMs: breedingWorkbenchApi.HARD_TIMEOUT_MS,
    meta: {
      repair_attempt: 1,
      missing_labels: missingLabels
    },
    onProgress: async (snapshot) => {
      syncResultFromPayload(snapshot)
    },
    onSoftTimeout: async (snapshot) => {
      syncResultFromPayload(snapshot)
      softTimeoutState.awaitingDecision = true
      return await new Promise((resolve) => {
        softTimeoutDecisionResolver.value = resolve
      })
    }
  })

const resolveSoftTimeoutDecision = (decision) => {
  if (typeof softTimeoutDecisionResolver.value === 'function') {
    softTimeoutState.awaitingDecision = false
    const resolver = softTimeoutDecisionResolver.value
    softTimeoutDecisionResolver.value = null
    resolver(decision)
  }
}

const handleContinueWaiting = () => {
  resolveSoftTimeoutDecision('continue')
}

const handleStopRun = () => {
  resolveSoftTimeoutDecision('stop')
}

const handleSubmit = async () => {
  const validationError = validateRequiredFields()
  if (validationError) {
    errorMessage.value = validationError
    message.warning(validationError)
    return
  }

  running.value = true
  currentMode.value = 'agent'
  errorMessage.value = ''
  resetResult()
  currentMode.value = 'agent'
  result.status = 'running'

  try {
    await ensureAgentContext()
    const context = buildSubmissionContext()
    const payload = await breedingWorkbenchApi.runBreedingWorkbench({
      agentId: selectedAgentId.value,
      agentConfigId: selectedAgentConfigId.value,
      trait: buildTrait(),
      question: buildVisibleQuestion(),
      context,
      title: `育种工作台：${buildVisibleQuestion().slice(0, 16) || DEFAULT_QUESTION}`,
      normalWaitMs: breedingWorkbenchApi.NORMAL_WAIT_MS,
      hardTimeoutMs: breedingWorkbenchApi.HARD_TIMEOUT_MS,
      onProgress: async (snapshot) => {
        syncResultFromPayload(snapshot)
      },
      onSoftTimeout: async (snapshot) => {
        syncResultFromPayload(snapshot)
        softTimeoutState.awaitingDecision = true
        return await new Promise((resolve) => {
          softTimeoutDecisionResolver.value = resolve
        })
      }
    })
    syncResultFromPayload({
      ...payload,
      toolName: payload.toolChain?.length === 1 ? payload.toolChain[0]?.name || '' : '',
      outputFiles:
        payload.finalMessageSource === 'tool' && payload.markdown
          ? ['以下为工具返回结果']
          : []
    }, { final: true })

    if (result.markdown && !evaluateBreedingCompliance(result.markdown).every((item) => item.passed)) {
      currentMode.value = 'repair'
      result.status = 'running'
      const repairPayload = await buildRepairPayload(payload.threadId, context, missingComplianceLabels.value)
      syncResultFromPayload({
        ...repairPayload,
        toolName: repairPayload.toolChain?.length === 1 ? repairPayload.toolChain[0]?.name || '' : '',
        outputFiles:
          repairPayload.finalMessageSource === 'tool' && repairPayload.markdown
            ? ['以下为工具返回结果']
            : []
      }, { final: true })
    }
  } catch (error) {
    console.error('Breeding workbench run failed:', error)
    const isStopped = error?.message === '已停止本次运行。'
    result.status = isStopped ? 'cancelled' : 'failed'
    errorMessage.value = error?.message || '育种工作台调用失败。'
    if (isStopped) {
      message.warning(errorMessage.value)
    } else {
      message.error(errorMessage.value)
    }
  } finally {
    softTimeoutState.awaitingDecision = false
    softTimeoutDecisionResolver.value = null
    running.value = false
  }
}

onMounted(async () => {
  try {
    await ensureAgentContext()
  } catch (error) {
    errorMessage.value = error?.message || '初始化育种工作台失败。'
  }
})
</script>

<style scoped lang="less">
.breeding-workbench-page {
  min-height: 100%;
  user-select: text;
  background:
    radial-gradient(circle at top right, rgba(125, 196, 180, 0.16), transparent 30%),
    linear-gradient(180deg, #f4faf8 0%, var(--gray-0) 100%);
}

.workbench-body {
  display: grid;
  grid-template-columns: minmax(320px, 390px) minmax(0, 1fr);
  gap: 20px;
  padding: 20px var(--page-padding) 28px;
}

.panel-intro {
  margin-bottom: 14px;

  h2 {
    margin: 0 0 8px;
    color: var(--gray-1000);
    font-size: 20px;
    font-weight: 600;
  }

  p {
    margin: 0;
    color: var(--gray-600);
    line-height: 1.7;
  }
}

.breeding-collapse {
  :deep(.ant-collapse-item) {
    margin-bottom: 12px;
    border: 1px solid var(--gray-100);
    border-radius: 18px;
    overflow: hidden;
    background: rgba(255, 255, 255, 0.94);
    box-shadow: 0 12px 36px rgba(19, 31, 23, 0.05);
  }

  :deep(.ant-collapse-header) {
    align-items: center;
    padding: 18px 20px !important;
    color: var(--gray-1000);
    font-size: 16px;
    font-weight: 600;
  }

  :deep(.ant-collapse-content-box) {
    padding: 0 20px 20px !important;
  }
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.single-column-grid {
  grid-template-columns: 1fr;
}

.field-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border: 1px solid var(--gray-100);
  border-radius: 14px;
  background: linear-gradient(180deg, var(--gray-0) 0%, #f8fcfb 100%);

  &.full-width {
    grid-column: 1 / -1;
  }
}

.field-label {
  color: var(--gray-700);
  font-size: 13px;
  font-weight: 500;
}

.file-input-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;

  &.dragging {
    :deep(.ant-input-affix-wrapper),
    :deep(.ant-input) {
      border-color: #1f9e86;
      box-shadow: 0 0 0 2px rgba(31, 158, 134, 0.12);
      background: rgba(220, 244, 238, 0.68);
    }
  }

  :deep(.ant-btn) {
    user-select: none;
  }

  :deep(.ant-input-affix-wrapper),
  :deep(.ant-input) {
    min-width: 0;
  }
}

.file-input-control {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;

  :deep(.ant-btn) {
    flex: 0 0 auto;
  }

  :deep(.ant-input-affix-wrapper),
  :deep(.ant-input) {
    flex: 1 1 auto;
    min-width: 0;
  }
}

.hidden-file-input {
  display: none;
}

.hint-text,
.hint-text,
.chain-chip,
.compliance-label,
.literature-doi,
.literature-quote,
.download-name,
.download-desc,
.result-block-body,
.artifact-pill {
  user-select: text;
}

.file-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 2px;
}

.file-chip {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 999px;
  background: #edf7f4;
  color: #167d73;
  font-size: 12px;
}

.hint-text {
  margin: 14px 0 0;
  color: var(--gray-600);
  line-height: 1.65;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 18px;

  :deep(.ant-btn-primary),
  :deep(.ant-btn) {
    user-select: none;
  }

  :deep(.ant-btn-primary) {
    border-color: #1b8f7a;
    background: linear-gradient(135deg, #1f9e86 0%, #167d73 100%);
  }
}

.chain-card,
.result-shell {
  padding: 18px 20px;
  border: 1px solid var(--gray-100);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 14px 40px rgba(19, 31, 23, 0.06);
}

.chain-card {
  margin-bottom: 16px;
}

.chain-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.chain-title {
  color: var(--gray-900);
  font-size: 14px;
  font-weight: 600;
}

.chain-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 10px;
  color: var(--gray-600);
  font-size: 12px;
}

.inline-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-label {
  color: var(--gray-600);
  font-size: 12px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid var(--gray-100);
  background: var(--gray-0);
  font-size: 12px;
  user-select: text;
}

.status-idle {
  color: var(--gray-700);
}

.status-running {
  border-color: rgba(26, 145, 118, 0.2);
  color: #15795f;
}

.status-success {
  border-color: rgba(38, 166, 91, 0.24);
  color: #217a3d;
}

.status-failed {
  border-color: rgba(233, 84, 84, 0.24);
  color: #c64646;
}

.chain-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.soft-timeout-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(235, 177, 49, 0.24);
  border-radius: 14px;
  background: rgba(255, 248, 226, 0.92);
}

.soft-timeout-text {
  flex: 1 1 320px;
  color: #8d6200;
  line-height: 1.6;
}

.soft-timeout-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chain-chip {
  display: inline-flex;
  align-items: center;
  padding: 7px 12px;
  border-radius: 999px;
  background: color-mix(in srgb, #1f9e86 14%, white);
  color: #187764;
  font-size: 13px;
}

.result-alert {
  margin-bottom: 16px;
}

.result-block-grid {
  display: grid;
  grid-template-columns: minmax(240px, 0.9fr) minmax(340px, 1.2fr) minmax(240px, 0.9fr);
  gap: 12px;
  margin-bottom: 16px;
}

.result-block {
  padding: 14px;
  border: 1px solid var(--gray-100);
  border-radius: 16px;
  background: linear-gradient(180deg, var(--gray-0) 0%, #f8fcfb 100%);
}

.result-block-title {
  margin-bottom: 10px;
  color: var(--gray-900);
  font-size: 14px;
  font-weight: 600;
}

.result-block-body {
  color: var(--gray-600);
  line-height: 1.7;
}

.compliance-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.compliance-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.compliance-label {
  color: var(--gray-800);
  font-size: 13px;
}

.compliance-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: currentColor;
  }

  &.passed {
    background: rgba(46, 174, 96, 0.14);
    color: #27784a;
  }

  &.missing {
    background: rgba(235, 177, 49, 0.16);
    color: #a26a06;
  }
}

.literature-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.literature-item {
  padding: 12px;
  border: 1px solid rgba(31, 158, 134, 0.14);
  border-radius: 12px;
  background: rgba(237, 247, 244, 0.65);
}

.literature-doi {
  margin-bottom: 6px;
  color: #136e63;
  font-size: 13px;
  font-weight: 600;
  word-break: break-all;
}

.literature-title {
  margin-bottom: 6px;
  color: var(--gray-800);
  font-size: 12px;
  line-height: 1.6;
}

.literature-quote {
  color: var(--gray-700);
  line-height: 1.7;
}

.download-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.download-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  border: 1px solid var(--gray-100);
  border-radius: 14px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
  user-select: none;

  &:hover:not(:disabled) {
    border-color: rgba(31, 158, 134, 0.28);
    box-shadow: 0 8px 20px rgba(17, 80, 67, 0.08);
    transform: translateY(-1px);
  }

  &:disabled {
    cursor: not-allowed;
    opacity: 0.58;
  }
}

.download-name {
  color: var(--gray-900);
  font-size: 13px;
  font-weight: 600;
}

.download-desc {
  color: var(--gray-600);
  font-size: 12px;
  line-height: 1.6;
}

.markdown-card {
  padding-top: 4px;
  user-select: text;

  :deep(.yk-markdown-preview) {
    user-select: text;
  }
}

.markdown-download-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;

  :deep(.ant-btn) {
    user-select: none;
  }
}

.diagnostic-collapse {
  margin-top: 18px;

  :deep(.ant-collapse-item) {
    border: 1px dashed var(--gray-200);
    border-radius: 14px;
    background: rgba(250, 252, 251, 0.88);
  }

  :deep(.ant-collapse-header) {
    padding: 12px 14px !important;
    color: var(--gray-800);
    font-weight: 600;
  }

  :deep(.ant-collapse-content-box) {
    padding: 0 14px 14px !important;
  }
}

.diagnostic-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 14px;
}

.diagnostic-item {
  display: flex;
  flex-direction: column;
  gap: 4px;

  span {
    color: var(--gray-600);
    font-size: 12px;
  }

  code {
    padding: 6px 8px;
    border-radius: 10px;
    background: #f3f7f6;
    color: var(--gray-900);
    font-size: 12px;
    word-break: break-all;
    user-select: text;
  }
}

@media (max-width: 1200px) {
  .workbench-body {
    grid-template-columns: 1fr;
  }

  .result-block-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 860px) {
  .field-grid {
    grid-template-columns: 1fr;
  }

  .diagnostic-grid {
    grid-template-columns: 1fr;
  }

  .file-input-control {
    flex-wrap: wrap;
  }

  .chain-card-top {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
