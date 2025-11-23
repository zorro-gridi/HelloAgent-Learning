<template>
  <div id="app" class="app-container">
    <Header />
    <ProcessNavigation />
    <MainContent />
    <Footer />
  </div>
</template>

<script setup lang="ts">
// 根组件 - 整合所有布局组件
import Header from './components/Layout/Header.vue'
import ProcessNavigation from './components/Layout/ProcessNavigation.vue'
import MainContent from './components/Layout/MainContent.vue'
import Footer from './components/Layout/Footer.vue'
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>