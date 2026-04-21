import { createRouter, createWebHistory } from 'vue-router'
import RaceDashboard from '../views/RaceDashboard.vue'
import NewCycle from '../views/NewCycle.vue'
import PromptEditor from '../views/PromptEditor.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/',        component: RaceDashboard, meta: { title: 'Dashboard' } },
    { path: '/new',     component: NewCycle,      meta: { title: 'Nuevo Ciclo' } },
    { path: '/prompts', component: PromptEditor,  meta: { title: 'Editar Prompts' } },
  ]
})
