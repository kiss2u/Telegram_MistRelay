<template>
  <div class="video-player-container">
    <video ref="videoPlayer" class="video-js vjs-big-play-centered"></video>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import videojs from 'video.js'
import 'video.js/dist/video-js.css'

const props = defineProps({
  src: {
    type: String,
    required: true
  },
  type: {
    type: String,
    default: '' 
  },
  options: {
    type: Object,
    default: () => ({})
  }
})

const videoPlayer = ref<HTMLVideoElement | null>(null)
let player: any = null

onMounted(() => {
  if (videoPlayer.value) {
    const defaultOptions = {
      controls: true,
      autoplay: true,
      preload: 'auto',
      fluid: true,
      sources: [{
        src: props.src,
        type: props.type
      }]
    }

    player = videojs(videoPlayer.value, { ...defaultOptions, ...props.options }, () => {
      console.log('player is ready')
    })
  }
})

onBeforeUnmount(() => {
  if (player) {
    player.dispose()
  }
})

// Watch for src changes to update player
watch(() => props.src, (newSrc) => {
  if (player) {
    player.src({ src: newSrc, type: props.type })
    player.play()
  }
})
</script>

<style scoped>
.video-player-container {
  width: 100%;
  height: 100%;
}
/* Ensure the player takes full width of container */
:deep(.video-js) {
  width: 100%;
  height: 100%;
}
</style>
