<template>
  <div class="video-player-container">
    <video ref="videoPlayer" class="video-js vjs-big-play-centered"></video>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';

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
  },
  remote: {
    type: String,
    default: ''
  },
  path: {
    type: String,
    default: ''
  }
});

import { ElNotification } from 'element-plus'

const videoPlayer = ref<HTMLVideoElement | null>(null);
let player: any = null; // Use any to avoid complex typing issues for now, or use ReturnType<typeof videojs>
let ws: WebSocket | null = null;

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
    };

    player = videojs(videoPlayer.value, { ...defaultOptions, ...props.options }, () => {
      console.log('player is ready');
    });
    
    // Connect to cache monitor
    if (props.remote && props.path) {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/api/rclone/cache/monitor?remote=${encodeURIComponent(props.remote)}&path=${encodeURIComponent(props.path)}`;
      
      try {
        ws = new WebSocket(wsUrl);
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.status === 'fully_cached') {
              ElNotification({
                title: '缓存完成',
                message: '视频已完全缓存，可以流畅拖动进度条',
                type: 'success',
                duration: 4500
              });
              ws?.close();
            }
          } catch (e) {
            console.error('WS parse error', e);
          }
        };
      } catch (e) {
        console.error('WebSocket init error', e);
      }
    }
  }
});

onBeforeUnmount(() => {
  if (player) {
    player.dispose();
  }
  if (ws) {
    ws.close();
  }
});

// Watch for src changes to update player
watch(() => props.src, (newSrc) => {
  if (player) {
    player.src({ src: newSrc, type: props.type });
    player.play();
    
    // Reconnect WS if source changes? 
    // Usually dialog is destroyed and recreated, so onMounted/onBeforeUnmount handles it.
    // If recycled, we might need logic here. But drive.vue uses v-if dialog, typically unmounts.
    // Actually drive.vue reuses the dialog but v-if="showPreview" on VideoPlayer might be toggled?
    // In drive.vue:
    // <VideoPlayer v-if="showPreview && previewType === 'video'" ... />
    // When showPreview becomes false, it unmounts. When true, mounts.
    // So onMounted is enough.
  }
});
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
