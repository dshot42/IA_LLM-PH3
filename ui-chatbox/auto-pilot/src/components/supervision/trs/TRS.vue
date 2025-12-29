<template>
    <div class="bar">
        <Bar id="trsBar" style="height: 50vh; width:70vw; margin:auto" v-if="scopeTRS.params.loading" :options="Diagram.chartOptions"
            :data="Diagram.chartData" />
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, type Ref } from "vue"

import { useI18n } from "vue-i18n"
const { t, locale } = useI18n({ useScope: "global" })

import { storeToRefs } from "pinia"
import useSupervisionStore from "@/stores/supervision/supervision"
const { scopeTRS } = storeToRefs(useSupervisionStore())

import { Bar } from "vue-chartjs"
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from "chart.js"

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)
const loading = ref(false)

class Diagram {
    public static chartData: any = {  
        labels: [], 
        datasets: [{
            label: 'TRS Repartition en %',
            data: [],
            backgroundColor: ['rgba(54, 162, 235, 0.2)'],
            borderColor: ['rgb(54, 162, 235)'],
            borderWidth: 1
        }],
    }

    public static chartOptions: any = {
        responsive: false,
        maintainAspectRatio: false,
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

const trsResult = computed(() => {
    return scopeTRS.value.params.loading
})

watch(trsResult, () => {

    if (!scopeTRS.value.params.loading)
        return;

    let color: any = {
        backgroundColor: [],
        borderColor: []
    }

    const avg: number = scopeTRS.value.result.trs.reduce(
        (accumulator: any, currentValue: any) => accumulator + currentValue,
    ) / scopeTRS.value.result.trs.filter((e: any) => e !=  undefined  &&  e != 0 ).length

    scopeTRS.value.result.trs.forEach((trs: any) => {
        color.backgroundColor.push(trs < avg ? 'rgb(255,0,0,0.2)' : 'rgb(0,128,0,0.2)')
        color.borderColor.push(trs < avg ? 'rgb(255,0,0)' : 'rgb(0,128,0)')
    });

    Diagram.chartData.labels = scopeTRS.value.params.queryFieldDisplay
    Diagram.chartData.datasets[0].data = scopeTRS.value.result.trs
    Diagram.chartData.datasets[0].backgroundColor = color.backgroundColor
    Diagram.chartData.datasets[0].borderColor = color.borderColor
})

</script>


