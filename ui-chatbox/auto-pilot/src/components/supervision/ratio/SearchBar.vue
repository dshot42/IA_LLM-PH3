<script setup lang="ts">
import { onMounted, ref, watch, type Ref } from "vue"
import { storeToRefs } from "pinia"
import mdiMagnify from "vue-material-design-icons/Magnify.vue"
import mdiAdd from "vue-material-design-icons/Plus.vue"
import mdiClear from "vue-material-design-icons/Close.vue"
import useSupervisionStore from "@/stores/supervision/supervision"
import { useI18n } from "vue-i18n"
import { computed } from "@vue/reactivity"
const { t } = useI18n({ useScope: "global" })
const {  scopeRatio } = storeToRefs(useSupervisionStore())
const { getProperty, getRatio } = useSupervisionStore()

const inputType = ref<Array<string>>(new Array())
const catSelect = ref<Array<string>>(new Array())
const searchContent = ref<Array<string>>(new Array())
const searchDateContent = ref<Array<Array<string>>>(new Array())
const displaySearchAlert = ref(false)
const nbSearchBar = ref(0)

const init = onMounted(() => {
    addSearchBar()
    getProperty()
})

init;

///////////////////////

function onSearch() {
    scopeRatio.value.param.loadingRatio = false
    scopeRatio.value.param.searchParam = {}
    displaySearchAlert.value = false
    for (let i = 0; i < catSelect.value.length; i++) {
        if (inputType.value[i] == "Input") {
            scopeRatio.value.param.searchParam[catSelect.value[i]+".keyword"] = searchContent.value[i]
        } else if (inputType.value[i] == "DatePicker") {
            scopeRatio.value.param.searchParam[catSelect.value[i]] = {
                date: {
                    gte: searchDateContent.value[i][0],
                    lte: searchDateContent.value[i][1],
                },
            } as never
        }
    }

    getRatio();
}

function onSelect() {
    inputType.value[nbSearchBar.value - 1] = scopeRatio.value.result.properties.has(catSelect.value[catSelect.value.length - 1])
        ? scopeRatio.value.result.properties.get(catSelect.value[catSelect.value.length - 1])!
        : "ERROR" // non present
}

function addSearchBar() {
    if (
        inputType.value[nbSearchBar.value - 1] == "" ||
        (inputType.value[nbSearchBar.value - 1] == "Input" && searchContent.value[nbSearchBar.value - 1].length == 0) ||
        (inputType.value[nbSearchBar.value - 1] == "DatePicker" &&
            searchDateContent.value[nbSearchBar.value - 1][0] == undefined &&
            searchDateContent.value[nbSearchBar.value - 1][1] == undefined)
    ) {
        displaySearchAlert.value = true
        return
    }

    inputType.value.push("")
    catSelect.value.push("")
    searchContent.value.push("")
    searchDateContent.value.push([])

    nbSearchBar.value++
}

function removeSearchBar() {
    inputType.value.pop()
    catSelect.value.pop()
    searchContent.value.pop()
    searchDateContent.value.pop()
    nbSearchBar.value--
    if (nbSearchBar.value == 0) {
        addSearchBar()
    }
    onSearch()
    console.log("nbSearchBar.value  " + nbSearchBar.value)
}

const catselected = computed(() => {
    return scopeRatio.value.param.selectedCat
})

watch(catselected, async () => {
    const length = nbSearchBar.value
    for (var i = 0; i < length; i++) {
        console.log("change catselected" + nbSearchBar.value)
        removeSearchBar()
    }
})
</script>

<template>
    <div class="search-container block">

        <div class="trace-search gridSearch" :class="displaySearchAlert ? 'horizontal-shaking' : ''"
            v-for="n in nbSearchBar">
            <Transition class="gridRow">
                <div >
                    <div style="margin-bottom: 5px">{{ t("tracing.menu.reference") }}</div>
                    <select  style="width:230px" :disabled="n < nbSearchBar && nbSearchBar > 1" :style="{
                            backgroundColor: n < nbSearchBar && nbSearchBar > 1 ? '#aeb0b3' : '#ffffff',
                        }" name="cat" id="catSelect" v-model="catSelect[n - 1]" @change="(event) => onSelect()">
                        <option value="" selected>-- selection --</option>
                        <option v-for="[key, type] in scopeRatio.result.properties" :value="key">{{
                            key.match(/((?!\.).)*$/)[0] }} {{ type == "DatePicker" ? "(date)" : "" }}</option>
                    </select>
                </div>
            </Transition>

            <Transition :duration="{ enter: 500, leave: 800 }" class="gridRow">
                <div>
                    <div :style="{ display: inputType[n - 1] != 'DatePicker' ? 'block' : 'none' }">
                        <div style="margin-bottom: 5px">{{ t("action.search") }}</div>
                        <mdiMagnify class="pi pi-search"></mdiMagnify>
                        <input v-model="searchContent[n - 1]" type="text" placeholder="..."
                            :disabled="(n < nbSearchBar && nbSearchBar > 1) || catSelect[n - 1] == ''"
                            @input="() => onSearch()" />
                    </div>

                    <div :style="{ display: inputType[n - 1] == 'DatePicker' ? 'block' : 'none' }">
                        <div style="display: grid; margin-bottom: 5px">
                            <span style="grid-row: 1">{{ t("tracing.menu.dategt") }} </span>
                            <span style="grid-row: 1">{{ t("tracing.menu.datelt") }}</span>
                        </div>
                        <div style="display: grid">
                            <div style="grid-row: 1; width: 300px">
                                <input :disabled="n < nbSearchBar && nbSearchBar > 1"
                                    v-model="searchDateContent[n - 1][0]" type="datetime-local"
                                    @input="() => onSearch()" />
                            </div>
                            <div style="grid-row: 1; width: 300px">
                                <input :disabled="n < nbSearchBar && nbSearchBar > 1"
                                    v-model="searchDateContent[n - 1][1]" type="datetime-local"
                                    @input="() => onSearch()" />
                            </div>
                        </div>
                    </div>
                </div>
            </Transition>

            <Transition  :duration="{ enter: 500, leave: 800 }" class="gridRow">
                <div v-if="n == nbSearchBar">
                    <div style="margin-bottom: 5px">Options</div>
                    <button class="addbtn" @click="addSearchBar()">
                        <mdiAdd class="mdiAdd"> </mdiAdd>
                    </button>
                    <button class="removebtn mdiClear" @click="removeSearchBar()">
                        <mdiClear class="mdiClear"> </mdiClear>
                    </button>
                </div>
            </Transition>
        </div>

        <div class="filterAlert" v-if="displaySearchAlert">
            {{
            catSelect[catSelect.length - 1].length == 0
            ? t("tracing.menu.displaySearchAlert.cat")
            : t("tracing.menu.displaySearchAlert.value") + "'" + catSelect[catSelect.length - 1] + "'"
            }}
        </div>
    </div>
</template>

<style >



</style>
