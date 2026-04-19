<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useProfile } from '../composables/useProfile'

const { fetchInsights, deleteInsight } = useProfile()

const insights = ref<any[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    insights.value = await fetchInsights()
  } finally {
    loading.value = false
  }
})

const totalTailorings = computed(() => {
  let total = 0
  for (const i of insights.value) total += (i.tailoring_count || 0)
  return total
})

async function removeInsight(id: number) {
  await deleteInsight(id)
  insights.value = insights.value.filter(i => i.id !== id)
}
</script>

<template>
  <div class="roles-page">
    <div class="roles-header">
      <div>
        <h2>Role Insights</h2>
        <p class="roles-desc">Learned automatically as you tailor resumes. Helps the AI understand your strengths for each role type.</p>
      </div>
      <div class="roles-stats" v-if="insights.length">
        <div class="stat">
          <div class="stat-value">{{ insights.length }}</div>
          <div class="stat-label">Role Types</div>
        </div>
        <div class="stat">
          <div class="stat-value">{{ totalTailorings }}</div>
          <div class="stat-label">Total Tailorings</div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="empty-state">Loading...</div>

    <div v-else-if="!insights.length" class="empty-state">
      No role insights yet. Tailor a resume to start building role-specific knowledge.
    </div>

    <div v-else class="roles-grid">
      <div v-for="insight in insights" :key="insight.id" class="role-card">
        <div class="role-header">
          <span class="role-name">{{ insight.role_type }}</span>
          <div class="role-header-right">
            <span class="role-count">{{ insight.tailoring_count }}x tailored</span>
            <button class="remove-btn" @click="removeInsight(insight.id)" title="Remove">&times;</button>
          </div>
        </div>

        <div v-if="insight.strongest_points?.length" class="role-section">
          <div class="role-label">Strongest Points</div>
          <ul>
            <li v-for="p in insight.strongest_points" :key="p">{{ p }}</li>
          </ul>
        </div>

        <div v-if="insight.preferred_skill_order?.length" class="role-section">
          <div class="role-label">Preferred Skill Order</div>
          <div class="skill-tags">
            <span v-for="(s, i) in insight.preferred_skill_order" :key="s" class="skill-tag">
              <span class="skill-rank">{{ Number(i) + 1 }}</span>{{ s }}
            </span>
          </div>
        </div>

        <div v-if="insight.frequently_modified_sections?.length" class="role-section">
          <div class="role-label">Frequently Modified</div>
          <div class="skill-tags">
            <span v-for="s in insight.frequently_modified_sections" :key="s" class="skill-tag mod-tag">{{ s }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.roles-page { max-width: 1200px; margin: 0 auto; }

.roles-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; gap: 20px; }
h2 { margin: 0; }
.roles-desc { color: #666; font-size: 0.82rem; margin: 4px 0 0; }
.roles-stats { display: flex; gap: 16px; flex-shrink: 0; }
.stat {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 10px;
  padding: 12px 20px; text-align: center;
}
.stat-value { font-size: 1.4rem; font-weight: 800; }
.stat-label { font-size: 0.7rem; color: #888; text-transform: uppercase; }

.empty-state {
  text-align: center; padding: 40px; color: #999; font-size: 0.9rem;
  background: #fff; border: 2px dashed #e0e0e0; border-radius: 12px;
}

.roles-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 12px;
}
.role-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 12px;
  padding: 16px;
}
.role-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.role-name { font-weight: 700; font-size: 1rem; text-transform: capitalize; }
.role-header-right { display: flex; align-items: center; gap: 8px; }
.role-count { color: #666; font-size: 0.78rem; }
.remove-btn {
  border: none; background: #f0f0f0; border-radius: 6px; width: 24px; height: 24px;
  font-size: 1rem; cursor: pointer; color: #999; display: flex; align-items: center; justify-content: center;
}
.remove-btn:hover { background: #ffe0e0; color: #d00; }

.role-section { margin-top: 10px; }
.role-label { font-size: 0.75rem; font-weight: 600; color: #555; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.3px; }
.role-section ul { margin: 0 0 0 16px; font-size: 0.84rem; }
.role-section li { margin-bottom: 2px; }

.skill-tags { display: flex; flex-wrap: wrap; gap: 5px; }
.skill-tag {
  background: #f0f0f0; border-radius: 6px; padding: 3px 10px;
  font-size: 0.78rem; color: #333; display: flex; align-items: center; gap: 4px;
}
.skill-rank { font-size: 0.65rem; font-weight: 700; color: #999; }
.mod-tag { background: #eef0ff; color: #4a5abb; }

@media (max-width: 700px) {
  .roles-grid { grid-template-columns: 1fr; }
  .roles-header { flex-direction: column; }
}
</style>
