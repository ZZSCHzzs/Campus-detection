<script setup lang="ts">
// 需集成地图库（如Leaflet）
</script>

<template>
  <div class="map-container">
    <div class="map" id="campus-map"></div>
    
    
  </div>
</template>

<style scoped>
.map-container {
  position: relative;
  height: 100vh;
}

#campus-map {
  width: 100%;
  height: 100%;
}

.legend {
  position: absolute;
  right: 20px;
  top: 20px;
  background: white;
  padding: 15px;
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(0,0,0,.1);
}

.color-box {
  display: inline-block;
  width: 20px;
  height: 20px;
  margin-right: 10px;
}
</style>