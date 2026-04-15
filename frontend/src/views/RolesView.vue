<script setup lang="ts">
import { ref, onMounted } from 'vue'
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

async function removeInsight(id: number) {
  await deleteInsight(id)
  insights.value = insights.value.filter(i => i.id !== id)
}
</script>

<template>
  <div class="roles-page">
    <h2>Roles</h2>
    <p class="roles-desc">Role insights are learned automatically as you tailor resumes. They help the AI understand your strengths for each role type.</p>

    <div v-if="loading" class="empty-state">Loading...</div>

    <div v-else-if="!insights.length" class="empty-state">
      No role insights yet. Tailor a resume to start building role-specific knowledge.
    </div>

    <div v-else class="roles-list">
      <div v-for="insight in insights" :key="insight.id" class="role-card">
        <div class="role-header">
          <span class="role-name">{{ insight.role_type }}</span>
          <span class="role-count">{{ insight.tailoring_count }}x tailored</span>
          <button class="remove-btn" @click="removeInsight(insight.id)">Remove</button>
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
            <span v-for="s in insight.preferred_skill_order" :key="s" class="skill-tag">{{ s }}</span>
          </div>
        </div>

        <div v-if="insight.frequently_modified_sections?.length" class="role-section">
          <div class="role-label">Frequently Modified Sections</div>
          <div class="skill-tags">
            <span v-for="s in insight.frequently_modified_sections" :key="s" class="skill-tag">{{ s }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.roles-page { max-width: 700px; margin: 0 auto; }
h2 { margin-bottom: 4px; }
.roles-desc { color: #666; font-size: 0.85rem; margin: 0 0 18px; }

.empty-state {
  text-align: center; padding: 40px; color: #999; font-size: 0.9rem;
  background: #fff; border: 2px dashed #e0e0e0; border-radius: 12px;
}

.roles-list { display: flex; flex-direction: column; gap: 10px; }
.role-card {
  background: #fff; border: 1px solid #e0e0e0; border-radius: 12px;
  padding: 16px;
}
.role-header {
  display: flex; align-items: center; gap: 10px; margin-bottom: 10px;
}
.role-name { font-weight: 700; font-size: 1rem; }
.role-count { color: #666; font-size: 0.8rem; }
.remove-btn {
  margin-left: auto; font-size: 0.75rem; background: none;
  border: 1px solid #ddd; border-radius: 6px; padding: 3px 10px;
  cursor: pointer; color: #dc3545;
}
.remove-btn:hover { background: #fff0f0; }

.role-section { margin-top: 8px; }
.role-label { font-size: 0.78rem; font-weight: 600; color: #555; margin-bottom: 4px; }
.role-section ul { margin: 0 0 0 18px; font-size: 0.85rem; }
.role-section li { margin-bottom: 2px; }

.skill-tags { display: flex; flex-wrap: wrap; gap: 5px; }
.skill-tag {
  background: #f0f0f0; border-radius: 6px; padding: 3px 10px;
  font-size: 0.78rem; color: #333;
}
</style>
