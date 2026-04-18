<script setup lang="ts">
import { ref } from 'vue'
import type { JobScoring, ATSResult } from '../stores/editor'

defineProps<{
  scoring: JobScoring | null
  atsResult: ATSResult | null
}>()

const expanded = ref(false)
const atsExpanded = ref(false)

function scoreColor(score: number): string {
  if (score >= 75) return '#28a745'
  if (score >= 50) return '#f0ad4e'
  return '#dc3545'
}

const categoryLabels: Record<string, string> = {
  contact_info: 'Contact Info',
  parsability: 'Parsability',
  keyword_match: 'Keyword Match',
  section_headers: 'Section Headers',
  date_format: 'Date Format',
  title_match: 'Title Match',
  hard_skills: 'Hard Skills',
  quantified_results: 'Quantified Results',
  experience_depth: 'Experience Depth',
}
</script>

<template>
  <div v-if="scoring || atsResult" class="score-panel">
    <div class="panel-header" @click="expanded = !expanded">
      <span class="panel-toggle">{{ expanded ? '-' : '+' }}</span>
      <span class="panel-title">Resume Scoring</span>
      <template v-if="scoring">
        <span class="quick-score" :style="{ color: scoreColor(scoring.before.overall_fit) }">
          Before: {{ scoring.before.overall_fit }}%
        </span>
        <template v-if="scoring.after">
          <span class="score-arrow">-></span>
          <span class="quick-score" :style="{ color: scoreColor(scoring.after.overall_fit) }">
            After: {{ scoring.after.overall_fit }}%
          </span>
        </template>
        <span v-else class="quick-score scoring-pending">After: ...</span>
      </template>
      <span v-if="atsResult" class="ats-badge" :style="{ background: scoreColor(atsResult.ats_score) }">
        ATS: {{ atsResult.ats_score }}
      </span>
    </div>

    <div v-show="expanded" class="panel-body">
      <!-- Before / After Comparison -->
      <div v-if="scoring" class="scores-grid">
        <div class="score-column">
          <h4>Before Tailoring</h4>
          <div class="score-row">
            <span class="score-label">Keyword Match</span>
            <span class="score-value" :style="{ color: scoreColor(scoring.before.keyword_match) }">{{ scoring.before.keyword_match }}%</span>
          </div>
          <div class="score-row">
            <span class="score-label">Skills Coverage</span>
            <span class="score-value" :style="{ color: scoreColor(scoring.before.skills_coverage) }">{{ scoring.before.skills_coverage }}%</span>
          </div>
          <div class="score-row">
            <span class="score-label">Experience Fit</span>
            <span class="score-detail">{{ scoring.before.experience_fit }}</span>
          </div>
          <div class="score-row">
            <span class="score-label">Overall Fit</span>
            <span class="score-value big" :style="{ color: scoreColor(scoring.before.overall_fit) }">{{ scoring.before.overall_fit }}%</span>
          </div>
        </div>

        <div class="score-column">
          <h4>After Tailoring</h4>
          <template v-if="scoring.after">
            <div class="score-row">
              <span class="score-label">Keyword Match</span>
              <span class="score-value" :style="{ color: scoreColor(scoring.after.keyword_match) }">{{ scoring.after.keyword_match }}%</span>
            </div>
            <div class="score-row">
              <span class="score-label">Skills Coverage</span>
              <span class="score-value" :style="{ color: scoreColor(scoring.after.skills_coverage) }">{{ scoring.after.skills_coverage }}%</span>
            </div>
            <div class="score-row">
              <span class="score-label">Experience Fit</span>
              <span class="score-detail">{{ scoring.after.experience_fit }}</span>
            </div>
            <div class="score-row">
              <span class="score-label">Overall Fit</span>
              <span class="score-value big" :style="{ color: scoreColor(scoring.after.overall_fit) }">{{ scoring.after.overall_fit }}%</span>
            </div>
          </template>
          <div v-else class="scoring-loading">
            <span class="loading-text">Scoring tailored resume...</span>
          </div>
        </div>
      </div>

      <!-- ATS Score Breakdown -->
      <div v-if="atsResult" class="ats-section">
        <div class="ats-header" @click="atsExpanded = !atsExpanded">
          <span class="ats-toggle">{{ atsExpanded ? '-' : '+' }}</span>
          <span class="ats-title">ATS Score: {{ atsResult.ats_score }}/100</span>
        </div>
        <div v-show="atsExpanded" class="ats-breakdown">
          <div v-for="(item, key) in atsResult.breakdown" :key="key" class="ats-row">
            <span class="ats-cat">{{ categoryLabels[key as string] || key }}</span>
            <div class="ats-bar-wrap">
              <div class="ats-bar" :style="{ width: item.score + '%', background: scoreColor(item.score) }"></div>
            </div>
            <span class="ats-score-num">{{ item.score }}</span>
            <span class="ats-detail">{{ item.detail }}</span>
          </div>
        </div>
        <p class="ats-verdict">{{ atsResult.brutal_verdict }}</p>
      </div>

      <!-- Gap Suggestions -->
      <div v-if="scoring && scoring.gap_suggestions.length" class="gaps-section">
        <h4>Profile Gaps</h4>
        <ul>
          <li v-for="(gap, i) in scoring.gap_suggestions" :key="i">{{ gap }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.score-panel {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 12px;
  box-shadow: 0 -2px 12px rgba(0,0,0,.08);
  position: sticky; bottom: 0; z-index: 10;
}
.panel-header {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 16px; cursor: pointer; user-select: none;
}
.panel-header:hover { background: #f8f8f8; border-radius: 12px; }
.panel-toggle { font-weight: 700; color: #666; width: 16px; }
.panel-title { font-weight: 700; font-size: 0.85rem; }
.quick-score { font-weight: 700; font-size: 0.85rem; }
.score-arrow { color: #999; font-size: 0.8rem; }
.ats-badge {
  margin-left: auto; color: #fff; font-weight: 700; font-size: 0.75rem;
  padding: 2px 10px; border-radius: 10px;
}

.panel-body { padding: 0 16px 14px; }

.scores-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 12px; }
.score-column h4 { margin: 0 0 8px; font-size: 0.8rem; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
.score-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.score-label { font-size: 0.78rem; color: #555; flex: 1; }
.score-value { font-weight: 700; font-size: 0.85rem; }
.score-value.big { font-size: 1.1rem; }
.score-detail { font-size: 0.75rem; color: #777; flex: 2; }

.ats-section { border-top: 1px solid #eee; padding-top: 10px; margin-bottom: 10px; }
.ats-header { display: flex; align-items: center; gap: 8px; cursor: pointer; margin-bottom: 6px; }
.ats-toggle { font-weight: 700; color: #666; width: 16px; }
.ats-title { font-weight: 700; font-size: 0.85rem; }
.ats-breakdown { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
.ats-row { display: flex; align-items: center; gap: 8px; font-size: 0.78rem; }
.ats-cat { width: 110px; color: #555; flex-shrink: 0; }
.ats-bar-wrap { flex: 1; height: 6px; background: #eee; border-radius: 3px; overflow: hidden; }
.ats-bar { height: 100%; border-radius: 3px; transition: width 0.3s; }
.ats-score-num { width: 28px; text-align: right; font-weight: 600; }
.ats-detail { color: #777; font-size: 0.72rem; flex: 2; }
.ats-verdict { font-size: 0.8rem; color: #444; font-style: italic; margin: 6px 0 0; line-height: 1.4; }

.scoring-pending { color: #999; font-style: italic; font-size: 0.8rem; }
.scoring-loading { padding: 12px 0; color: #999; font-size: 0.8rem; font-style: italic; }
.loading-text { animation: pulse 1.5s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

.gaps-section { border-top: 1px solid #eee; padding-top: 10px; }
.gaps-section h4 { margin: 0 0 6px; font-size: 0.8rem; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
.gaps-section ul { margin: 0; padding-left: 18px; }
.gaps-section li { font-size: 0.8rem; color: #c00; margin-bottom: 3px; line-height: 1.3; }
</style>
