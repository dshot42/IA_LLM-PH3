<script setup lang="ts">
import { onMounted, ref, watch, type Ref } from "vue"
import { storeToRefs } from "pinia"
import useSupervisionStore from "@/stores/supervision/supervision"
import mdiMagnify from "vue-material-design-icons/Magnify.vue"
import { useI18n } from "vue-i18n"
const { t } = useI18n({ useScope: "global" })
const { scopeTRS, constante } = storeToRefs(useSupervisionStore())
const { getTRS, convertDate } = useSupervisionStore()


const selectedMonth = ref("*")
const selectedYear = ref("*")

const dayInMs:number = 24 * 60 * 60 * 1000


function setQueryField() {
    const queryField: Array<any> = []
    const queryFieldDisplay: Array<string> = []

    if (scopeTRS.value.params.mode != 3) { //fix // slided

        let refDate: Date = new Date();
        if (scopeTRS.value.params.mode == 1) {
            refDate = new Date(new Date(new Date().setMonth(0)).setDate(1))
            if (selectedYear.value != "*") {
                refDate = new Date(refDate.setFullYear(parseInt(selectedYear.value)))
                if (selectedMonth.value != "*") {
                    refDate = new Date(refDate.setMonth(parseInt(selectedMonth.value)))
                }
            }
        }
        else {
            refDate = new Date(scopeTRS.value.params.slideDate)
        }

        if ((scopeTRS.value.params.mode == 1 && selectedYear.value == "*") ||
            (scopeTRS.value.params.mode == 2 && scopeTRS.value.params.period == 'year')) {

            //fix et slid sont identique pour le cas des années
            const displayYear = 5
            refDate = new Date(refDate.setFullYear(refDate.getFullYear() -
                (scopeTRS.value.params.mode == 2 ? (displayYear - 1) / 2 : displayYear - 1)))

            for (var i = 0; i <= displayYear; i++) { // +1 pour interval avec année suivante
                queryField.push(new Date(refDate))
                if (i < displayYear) {
                    queryFieldDisplay.push(new Date(refDate).getFullYear().toString())
                }
                refDate = new Date(refDate.setFullYear(refDate.getFullYear() + 1))
            }
        }
        else if ((scopeTRS.value.params.mode == 1 && selectedMonth.value == "*") ||
            (scopeTRS.value.params.mode == 2 && scopeTRS.value.params.period == 'month')) {  //all month of a specifique year 

            if (scopeTRS.value.params.mode == 2) {
                refDate = new Date(new Date(refDate.setMonth(refDate.getMonth() - 6)).setDate(1)) // slide
            }

            for (var i = 0; i <= 12; i++) { // +1 pour interval avec mois suivant   
                queryField.push(new Date(refDate))
                console.log(queryField)
                if (i < 12) {
                    queryFieldDisplay.push(constante.value.month[new Date(refDate).getMonth()] + " " + new Date(refDate).getFullYear())
                }

                refDate = new Date(refDate.setMonth(refDate.getMonth() + 1))
            }

        } else if ((scopeTRS.value.params.mode == 1 && selectedMonth.value != "*") ||
            (scopeTRS.value.params.mode == 2 && scopeTRS.value.params.period == 'day')) { // all day of a specific month of a specific year

            let dateFrom: Date = (scopeTRS.value.params.mode == 1) ?
                new Date( new Date(refDate).setDate(1))
                :
                new Date( new Date(refDate).setDate(refDate.getDate() - 15))

            let dateToMoove = new Date(dateFrom)
            const dateTo: Date = (scopeTRS.value.params.mode == 1) ?
                new Date( new Date(dateToMoove).setMonth(dateToMoove.getMonth() +1))
                :
                new Date( new Date(dateToMoove).setDate(dateToMoove.getDate() + 30))

            while (new Date(dateFrom) <= new Date(dateTo)) {
                queryField.push(new Date(dateFrom))
                if (dateFrom < dateTo)
                    queryFieldDisplay.push(convertDate(new Date(dateFrom).toString()))

                dateFrom = new Date(dateFrom.setDate(dateFrom.getDate() + 1))
            }
            console.log(queryField)
        }
    }
    else {// slide => interval
        const datediff = (Date.parse(scopeTRS.value.params.interval.to)
            -
            Date.parse(scopeTRS.value.params.interval.from)) / dayInMs

        for (var i = 0; i < datediff + 1; i++) {
            const newDate = new Date(new Date(scopeTRS.value.params.interval.from)
                .setDate(new Date(scopeTRS.value.params.interval.from).getDate() + i))
            console.log(newDate)
            queryField.push(newDate)
            queryFieldDisplay.push(convertDate(newDate.toString()))
        }            
    }
   
    scopeTRS.value.params.queryFieldDisplay = queryFieldDisplay
    scopeTRS.value.params.queryField = queryField
}

onMounted(() => {
    searchTRS() // init
})

async function searchTRS() {
    scopeTRS.value.result.trs = new Array<any>()
    scopeTRS.value.params.loading = false
    setQueryField();
    for (var i = 0; i < scopeTRS.value.params.queryField.length - 1; i++) {
        scopeTRS.value.params.request = {
            search: {
                date: {
                    date: {
                        gte: scopeTRS.value.params.queryField[i],
                        lt: scopeTRS.value.params.queryField[i + 1],
                    },
                },
            },
            aggs: {
                trsPercent:
                {
                    avg: { field: "trsPercent" }
                },
            },
        }
        const data = await getTRS()
        console.log(scopeTRS.value.params.queryField[i] +" => " ,data)
    }
    scopeTRS.value.params.loading = true
    // console.log(scopeTRS.value.params.queryField)
}


function intervalBetweenDayInput() {
   return  (new Date(scopeTRS.value.params.interval.to).getTime() - new Date(scopeTRS.value.params.interval.from).getTime()) / dayInMs
}
</script>

<template>
    <div class="search-container block" style="padding:20px">

        <div class="trace-search gridSearch gridRow">
            <div class="gridSearch">
                <div class="gridRow">
                    <legend style="margin-bottom: 5px">Type de période </legend>
                    <fieldset style="width: 300px;padding: 10px;">
                        <div style="display:block">
                            <input type="radio" name="periodOption" value="fixed" style=" margin: 0.4rem; width: 50px;"
                                @click="scopeTRS.params.mode = 1" :checked="scopeTRS.params.mode == 1">
                            <label for="periodOption"> Fixed </label>
                        </div>
                        <div style="display:block">
                            <input type="radio" name="periodOption" value="slided" style=" margin: 0.4rem; width: 50px;"
                                @click="scopeTRS.params.mode = 2" :checked="scopeTRS.params.mode == 2">
                            <label for="periodOption"> Slided </label>
                        </div>
                        <div style="display:block">
                            <input type="radio" name="periodOption" value="accurate" style=" margin: 0.4rem; width: 50px;" 
                                @click="scopeTRS.params.mode = 3"
                                :checked="scopeTRS.params.mode == 3">
                            <label for="periodOption"> Accurate </label>
                        </div>
                    </fieldset>
                </div>

                <div class="gridRow">
                    <div style="margin-bottom: 5px">Selectionner ligne</div>
                    <select class="catSelect" v-model="scopeTRS.params.line">
                        <option value="*" selected>all lines</option>
                        <option v-for="l in scopeTRS.lines" :value="l.id">{{ l.id }}</option>
                    </select>
                </div>
            </div>


            <div v-if="scopeTRS.params.mode == 1" class="gridSearch" >
                <div class="gridRow" >
                    <div style=" margin-top:15px">Selectionner année</div>
                    <select class="catSelect" v-model="selectedYear">
                        <option value="*" selected>all years</option>
                        <option v-for="y in constante.years" :value="y">{{
                            y }}</option>
                    </select>
                </div>

                <div class="gridRow" v-if="selectedYear != '*'">
                    <div>Selectionner mois</div>
                    <select class="catSelect" v-model="selectedMonth">
                        <option value="*" selected>all month</option>
                        <option v-for="(m,i) in constante.month" :value="i">{{ m }}</option>
                    </select>
                </div>
            </div>

            <div v-if="scopeTRS.params.mode != 1">
                <div v-if="scopeTRS.params.mode == 2" class="gridSearch" >
                    <div class="gridRow">
                        <div style="margin-bottom: 5px; margin-top:15px">Période</div>
                        <select class="catSelect" v-model="scopeTRS.params.period">
                            <option value="year" selected>year</option>
                            <option value="month">month</option>
                            <option value="day">day</option>
                        </select>
                    </div>
                    <div class="gridRow">
                        <div style="margin-bottom: 5px; margin-top:15px"> Date</div>
                        <input :disabled="false" v-model="scopeTRS.params.slideDate" type="date" />
                    </div>
                </div>

                <div class="gridRow" v-if="scopeTRS.params.mode == 3">
                    <div class="gridSearch">
                        <div class="gridRow">
                            <div style="margin-bottom: 5px; margin-top:15px"> Date > à</div>
                            <input :disabled="false" v-model="scopeTRS.params.interval.from" type="date" />
                        </div>
                        <div style="margin-left:20px" class="gridRow">
                            <div style="margin-bottom: 5px; margin-top:15px"> Date < à</div>
                                    <input :disabled="false" v-model="scopeTRS.params.interval.to" type="date" />
                            </div>
                        </div>

                        <div style="color:red" v-if="intervalBetweenDayInput() > 60"> Interval {{
                            intervalBetweenDayInput() +" > 60 days" }}</div>
                    </div>
                </div>
            </div>

            <div class="gridRow searchBtn">
                <button @click="searchTRS()" :disabled="(scopeTRS.params.mode == 3 && intervalBetweenDayInput() > 60)">
                    <mdiMagnify></mdiMagnify>
                    <span>Search</span>
                </button>
            </div>

        </div>
</template>

<style scoped>
.search-container {
    background-color: #ffffff;
    box-shadow:
        rgba(50, 50, 93, 0.25) 0px 2px 5px -1px,
        rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
    display:grid;
    grid-template-columns: auto 150px;
}

.gridSearch {
    display: grid;
    font-size: 16px;
    vertical-align: middle;
    grid-template-columns: 400px auto;
    margin-bottom: 0px;
}


.gridRow {
    grid-row: 1;
    display: inline;
}

.gridRow {
    -webkit-animation: slide-right 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
    animation: slide-right 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
}

.searchBtn {
    display: flex;
    align-items: end;
    width: 100%;
}

.searchBtn>button {
    background-color: #4754d1;
    color: white;
    height: 50px;
    margin-left: auto;
    padding: 10px;
}

.catSelect {
    width: 300px;
    display: inline;
    padding: 15px 15px;
    background: white;
    background-size: 15px 15px;
    font-size: 18px;
    border: none;
    border-radius: 5px;
    box-shadow:
        rgba(50, 50, 93, 0.25) 0px 2px 5px -1px,
        rgba(0, 0, 0, 0.3) 0px 1px 3px -1px;
}


</style>
