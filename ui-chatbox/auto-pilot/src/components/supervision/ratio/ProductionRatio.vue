<template>
    <div class="DoughnutGrid">
        <div class="DoughnutChart" v-for="line of Object.keys(listDiag)">
            <div name="DoughnutChart" style=" text-align: center; width:auto">Répartition de la production sur la ligne :  {{ line }}
            </div>
            <Doughnut v-if="!scopeRatio.param.loadingRatio" :options="Diagram.chartOptions" :data="listDiag[line]" />
        </div>
    </div>
</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n"
const { t, locale } = useI18n({ useScope: "global" })

import { storeToRefs } from "pinia"
import useSupervisionStore from "@/stores/supervision/supervision"
const {  scopeRatio } = storeToRefs(useSupervisionStore())
const { getRatio } = useSupervisionStore()

import { onMounted, computed, ref, watch } from "vue"
import { Chart as ChartJS, Title, ArcElement, Tooltip, Legend } from "chart.js"
import { Doughnut } from "vue-chartjs"

ChartJS.register(ArcElement, Tooltip, Legend)


class Diagram {

    public chartData:any = {
        labels: ["GOOD", "BAD"],
        datasets: [
            {
                backgroundColor: ["green", "red"],
                data: Array,
            },
        ],
     }
    
    public static chartOptions:any =  {
        responsive: false,
        animation: {
            duration: 2000,
        },
        plugins: {
            legend: {
                display: true,
                text: "Custom Chart Title",
            },
        },
    }
}

let listDiag:any = {
    whole: new Diagram().chartData,
    l1: new Diagram().chartData,
    l2: new Diagram().chartData,
    l3: new Diagram().chartData,
}

onMounted(() => {
    getRatio() // init
})


const ratio = computed(() => {
    return scopeRatio.value.param.loadingRatio
})

watch(ratio, async () => {
    scopeRatio.value.result.countRatio.forEach((data: Map<string, number>, line: string) => {
        listDiag[line].datasets[0].data = Array.from(data.values())
    })
})

</script>

<style>

.DoughnutGrid {
    display: grid;
    border-radius: 3px;
    font-size: 16px;
    vertical-align: middle;
    grid-template-columns: repeat(4, 1fr);
    width :100%;
    margin:auto;
}


.DoughnutChart {
    height: auto;
    grid-row: 1;
    display: inline-block;
    margin: auto;
}

.DoughnutChart {
    height: auto;
    grid-row: 1;
    display: inline-block;
    margin: auto;
}
</style>
