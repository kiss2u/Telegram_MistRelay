<template>
  <div id="app">
    <router-view v-if="route.meta.public" />
    <AppLayout v-else />
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import AppLayout from '@/components/layout/app-layout.vue'

const route = useRoute()
</script>
