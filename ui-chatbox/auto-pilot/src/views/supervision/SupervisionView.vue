<script setup lang="ts">
import '../../assets/searchBar.css'
import TRSView from './TRSView.vue';
import RatioView from './RatioView.vue';
import Alert from './AlertView.vue';
import { ref } from 'vue';

const selected = ref(1)
</script>

<template>
    <div class="supervisionGrid ">
        <div class="supervisionMenu block">
            <button :class="selected == 1 ? 'supervisionSelected': ''" @click="selected = 1">TRS</button>
            <button :class="selected == 2 ? 'supervisionSelected' : ''" @click="selected = 2">Production Rendement</button>
            <button :class="selected == 3 ? 'supervisionSelected' : ''" @click="selected = 3">Evenement de production</button>
        </div>
        <div class="supervisionPanel">
            <TRSView v-if="selected == 1" />
            <RatioView v-if="selected== 2" />
            <Alert v-if="selected == 3" />
        </div>
    </div>
</template>

<style scoped>

  .supervisionGrid {
    display: grid;
    border-radius: 3px;
    font-size: 16px;
    vertical-align: middle;
    grid-template-columns: 20% 80%; 
    margin-bottom: 20px;
  }

.supervisionPanel, .supervisionMenu {
    grid-row: 1;
    display: inline;
}

.supervisionMenu > button {
    color: #4754d1;
    border : solid #4754d1 2px;
    background-color: #f6f9ff;
    text-align: center;
    margin: 10px 0px 10px 0px;
    width: 100%;
    height: 60px;
    text-transform: uppercase;
    font-size: 14px;
}

.supervisionMenu> .supervisionSelected,  .supervisionMenu>button:hover{
    color: white;
    background-color: #4754d1;
}
  

</style>
