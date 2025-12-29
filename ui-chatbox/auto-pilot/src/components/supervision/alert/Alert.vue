<template>
    <div class="search-container trace-search block" style="padding:20px">
        <div style="display:grid">
            <div class="gridRow">
                <div style="margin-bottom: 5px"> Date > à</div>
                <input :disabled="false" v-model="scopeEventAlert.params.interval.from" type="date"
                    @change="searchAlertSum()" :value="new Date(scopeEventAlert.params.interval.from).toISOString().substring(0,10)"/>
            </div>
            <div style="margin-left:20px" class="gridRow">
                <div style="margin-bottom: 5px"> Date < à</div>
                        <input :disabled="false" v-model="scopeEventAlert.params.interval.to" type="date"
                            @change="searchAlertSum()" :value="new Date(scopeEventAlert.params.interval.to).toISOString().substring(0,10)"/>
                </div>
            </div>
        </div>

        <div class="diag">
            <!-- diagram repartition system  -->
            <PolarArea style="height:65vh; margin:auto" v-if="scopeEventAlert.params.loading" :options="MainDiagram.chartOptions"
                :data="listDiag['whole']" />
        </div>

        <PopupModal class="modal-container" ref="supervisionModal">
            <template #header>
                <div>Répartition des alertes sur le systeme : {{ keyDetail }}
                </div>
            </template>
            <template #content>
                <div class="tabs">
                    <div class="tab" :class="choicePeriod == 'year' ?'selected':''" @click="choicePeriod ='year'">Year
                    </div>
                    <div class="tab" :class="choicePeriod == 'month' ? 'selected' : ''" @click="choicePeriod = 'month'">
                        Month</div>
                    <div class="tab" :class="choicePeriod == 'day' ? 'selected' : ''" @click="choicePeriod = 'day'">Day
                    </div>
                </div>
                <div v-if="!scopeEventAlert.details.params.loading" class="detail-loading">
                    <div class="loader"></div>
                    <div>LOADING SYSTEM DETAILS, PLEASE WAIT...</div>
                </div>
                <div v-if="scopeEventAlert.details.params.loading" v-for="v in DiagramElement">
                    <Bar v-if=" choicePeriod == v.period" style="width:70vw; height:40vh; margin:30px"
                        :options="DetailsDiag.chartOptions" :data="v.element" />
                </div>
            </template>
            <template #footer>
                <button class="primary" @click="closePopup">OK</button>
            </template>
        </PopupModal>

</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n"
const { t, locale } = useI18n({ useScope: "global" })

import { storeToRefs } from "pinia"
import useSupervisionStore from "@/stores/supervision/supervision"
const {  scopeEventAlert,constante } = storeToRefs(useSupervisionStore())
const { getAlertSum, getDetailsOfSupervisionSystem } = useSupervisionStore()

import { onMounted, computed, ref, watch, type Ref } from "vue"

import { PolarArea } from 'vue-chartjs'
import { Bar } from 'vue-chartjs'

import {
    Chart as ChartJS,
    RadialLinearScale,
    ArcElement,
    Tooltip,
    Legend,
    LinearScale,
    CategoryScale,
    BarElement,
} from 'chart.js'


ChartJS.register(RadialLinearScale, BarElement, LinearScale, ArcElement, CategoryScale, Tooltip, Legend)


function randomColor(i:number) {

    var colorArray = ['rgb(255, 99, 132)',
        'rgb(75, 192, 192)',
        'rgb(255, 205, 86)',
        'rgb(54, 162, 235)',"#1abc9c", "#2ecc71", "#3498db", "#9b59b6", "#34495e", "#16a085", "#27ae60", "#2980b9", "#8e44ad", "#2c3e50", "#f1c40f", "#e67e22", "#e74c3c", "#f39c12", "#d35400", "#c0392b", "#7f8c8d"]


    return colorArray[i] //Math.floor(Math.random() * colorArray.length-1)];
}

class MainDiagram {
    public chartData:any = {
        labels: new Array(),
        datasets: [
            {
                label: 'Nombre d\'alerte global :',
                backgroundColor: new Array(),
                data: new Array(),
            },
        ],
     }
    
    public static chartOptions: any = {
        onClick: (event: any, elements: any, chart: any) => {
            if (elements[0]) {
                const i = elements[0].index;
                showDetails(chart.data.labels[i])
            }
        },
        responsive: false,
        animation: {
            duration: 2000,
        },
        plugins: {
            legend: {
                position: 'top',
            },
            title: {
                display: true,
                text: 'Répartition des alertes survenues par systeme'
            },
            chart: {
                type: 'polarArea',
            },
            stroke: {
                colors: ['#fff']
            },
            fill: {
                opacity: 0.8
            },
        }
    }
}

async function searchAlertSum() {
    scopeEventAlert.value.params.request = {
        search: {
            "message.messageTimestamp": {
                date: {
                    gte: scopeEventAlert.value.params.interval.from,
                    lt: scopeEventAlert.value.params.interval.to,
                },
            },
        },
        "aggs": {
            "count": {
                "terms": {
                    "field": "message.messageTemplateParameters.productionSystem.keyword", // keyword
                },
            },     
        }
    }

    await getAlertSum() // init
    listDiag['whole'] = new MainDiagram().chartData

    scopeEventAlert.value.result.countPerSystem.forEach((data: any,i) => {
        listDiag['whole'].datasets[0].data.push(data.doc_count)
        listDiag['whole'].labels.push(data.key)
        listDiag['whole'].datasets[0].backgroundColor.push(randomColor(i))
    })
    
    scopeEventAlert.value.params.loading = true

}

onMounted(() => {
    searchAlertSum();
})


let listDiag: any = {
    whole: new MainDiagram().chartData, 
    l1: new MainDiagram().chartData,// not implemented
    l2: new MainDiagram().chartData,// not implemented
    l3: new MainDiagram().chartData, // not implemented
}


///// Modal ///////
import PopupModal from "@/components/PopupModal.vue"

const choicePeriod = ref('year')
const keyDetail = ref()
let DiagramElement = [] as Array<any>


const supervisionModal = ref<InstanceType<typeof PopupModal>>()
const closePopup = () => {
     searchAlertSum();
    supervisionModal.value?.close()

}

const showDetails = (key: string) => {
    supervisionModal.value?.open()
    keyDetail.value = key
    // request 
    console.log("showDetails")
    setIntervalQuery()
}

async function setIntervalQuery() {
    let refDate= new Date(new Date().setFullYear(new Date().getFullYear() , 0, 1))
    scopeEventAlert.value.details.params.loading = false
    DiagramElement = []
    // année 5 an last
    // mois 12 mois last
    // jour => 30  last

    //year
    let list = new Array<Array<Date>>()
    let delta = 6

    for (let i = 1; i <= delta; i++) {
        list.push([new Date(new Date(refDate).setFullYear(new Date(refDate).getFullYear() - delta + i)), new Date(new Date(refDate).setFullYear(new Date(refDate).getFullYear() - delta + i+1) ) ])
    }
    DiagramElement.push({
        period: 'year',
        element: new DetailsDiag().chartData,
        interval: list
    })


    // month
     refDate = new Date(new Date(new Date().setMonth(new Date().getMonth() -12)).setDate(1))

    list = new Array<Array<Date>>()
    delta = 12
    for (let i = 0; i <= delta; i++) {
        list.push([new Date(new Date(refDate).setMonth(new Date(refDate).getMonth()+ i)), new Date(new Date(refDate).setMonth(new Date(refDate).getMonth() +i+1))])
    }
    console.log(list)
    DiagramElement.push({
        period: 'month',
        element: new DetailsDiag().chartData,
        interval: list
    })


    // day 
    refDate = new Date()
    list = new Array<Array<Date>>()
    delta = 31
    for (let i = 1; i <= delta; i++) {
        list.push([new Date(new Date(refDate).setDate(new Date(refDate).getDate() - delta + i)), new Date(new Date(refDate).setDate(new Date(refDate).getDate() - delta + i+1))])
    }
    DiagramElement.push({
        period: 'day',
        element: new DetailsDiag().chartData,
        interval: list
    })
    await searchModalDetailsOnTime()
    console.log(DiagramElement)
    scopeEventAlert.value.details.params.loading = true

}

class DetailsDiag {

    public chartData: any = {
        labels: new Array(),
        datasets: [
            {
                label: keyDetail.value,
                borderColor: '#4754d1',
                backgroundColor: "#4754d1",
                fill: 1,
                tension: 0.5,
                animations: {
                    y: {
                        duration: 1000,
                        delay: 0
                    }
                },
                data: new Array(),
            },
        ],
    }

    public static chartOptions: any = {
        responsive: false,
        plugins: {
            legend: {
                display: true,
                text: "Custom Chart Title",
            },
        },
    }
}


 async function searchModalDetailsOnTime() {

    for (let el of DiagramElement) {
        el.element = new DetailsDiag().chartData
        for (let int of el.interval) {
            scopeEventAlert.value.details.params.request = {
                search: {
                    "message.messageTemplateParameters.productionSystem": keyDetail.value,
                    "message.messageTimestamp": {
                        date: {
                            gte: int[0],
                            lt: int[1],
                        },
                    },
                },
                "aggs": {
                    "count": {
                        "terms": {
                            "field": "message.messageTemplateParameters.productionSystem.keyword", // keyword
                        },
                    },
                }
            }

            console.log(scopeEventAlert.value.details.params.request)
            const data = (await getDetailsOfSupervisionSystem())
            const label = el.period == 'year' ?
                    new Date(int[0]).getFullYear().toString()
                :
                el.period == 'month' ?
                constante.value.month[new Date(int[0]).getMonth()]+ " "+ new Date(int[0]).getFullYear().toString()
                :
                int[0].toLocaleDateString('fr-FR')
            el.element.labels.push(label)
            el.element.datasets[0].data.push(data.length ? data[0].doc_count : 0)
        }
       
    }
}

</script>

<style scoped>

.diag {
    width : 55%;
    margin : auto;
}



</style>
