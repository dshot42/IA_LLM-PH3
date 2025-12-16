<script setup lang="ts">
import { ref, onMounted } from "vue"

/* CONFIG */
const host = "192.168.1.24"

/* STATE */
const messages = ref<any[]>([])
const message = ref("")
const sqlSwitch = ref(false)
const isLoading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

/* HELPERS */
function addMessage(text: string, sender: "user" | "ai") {
  messages.value.push({ text, sender, type: "text" })
  scrollBottom()
}

function addSQLMessage(data: any) {
  messages.value.push({ data, sender: "ai", type: "sql" })
  scrollBottom()
}

function addImage(src: string, sender: "user" | "ai") {
  messages.value.push({ src, sender, type: "image" })
  scrollBottom()
}

function addLoader() {
  isLoading.value = true
}

function removeLoader() {
  isLoading.value = false
}

function scrollBottom() {
  requestAnimationFrame(() => {
    const el = document.getElementById("chatbox")
    if (el) el.scrollTop = el.scrollHeight
  })
}

/* SEND TEXT */
async function sendMessage() {
  if (!message.value.trim()) return

  addMessage(message.value, "user")
  const prompt = message.value
  message.value = ""

  addLoader()

  const url = sqlSwitch.value
    ? `http://${host}:11434/api/sql`
    : `http://${host}:11434/api/generate`

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt })
    })

    const data = await res.json()
    removeLoader()

    if (sqlSwitch.value) {
      addSQLMessage(data)
    } else {
      addMessage(data.reply || data, "ai")
    }
  } catch (e: any) {
    removeLoader()
    addMessage("Erreur : " + e.message, "ai")
  }
}

/* IMAGE UPLOAD */
function onFileChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = () => {
    const img = new Image()
    img.onload = async () => {
      const canvas = document.createElement("canvas")
      const ctx = canvas.getContext("2d")!

      const maxWidth = 300
      const scale = maxWidth / img.width
      canvas.width = maxWidth
      canvas.height = img.height * scale

      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
      const img64 = canvas.toDataURL("image/jpeg", 0.8)

      addImage(img64, "user")
      addLoader()

      try {
        const res = await fetch(`http://${host}:11434/api/prompt/image`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: img64 })
        })

        const data = await res.json()
        removeLoader()
        addMessage(data.reply, "ai")
      } catch (e: any) {
        removeLoader()
        addMessage("Erreur image", "ai")
      }
    }
    img.src = reader.result as string
  }
  reader.readAsDataURL(file)
}
</script>

<template>
  <div class="page">

    <!-- CHAT -->
    <div id="chatbot-block">
      <div id="chatbox">
        <div
          v-for="(m, i) in messages"
          :key="i"
          class="msg"
          :class="m.sender"
        >
          <template v-if="m.type === 'text'">
            {{ m.text }}
          </template>

          <template v-if="m.type === 'image'">
            <img :src="m.src" style="width:150px" />
          </template>

          <template v-if="m.type === 'sql'">
            <table>
              <thead>
                <tr>
                  <th v-for="h in m.data.header" :key="h">{{ h }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(r, idx) in m.data.content" :key="idx">
                  <td v-for="h in m.data.header" :key="h">
                    {{ r[h] }}
                  </td>
                </tr>
              </tbody>
            </table>
          </template>
        </div>

        <div v-if="isLoading" class="msg ai loader">
          ⏳ L'IA réfléchit...
        </div>
      </div>
    </div>

    <!-- INPUT -->
    <div id="inputArea">
      <textarea
        v-model="message"
        placeholder="Rechercher prompt..."
        @keydown.enter.prevent="sendMessage"
      />

      <button class="upload-btn" @click="fileInput?.click()">
        📎
        <input
          ref="fileInput"
          type="file"
          class="file-input"
          @change="onFileChange"
        />
      </button>

      <button id="sendBtn" @click="sendMessage">Envoyer</button>
    </div>

    <label>
      <input type="checkbox" v-model="sqlSwitch" />
      SQL Request
    </label>
  </div>
</template>

<style scoped>


   .tab {
        padding: 10px 20px;
        border-radius: 6px 6px 0 0;
        cursor: pointer;
        background: #ccc;
        margin-right: 2px;
    }
    .tab.active {
        background: #0078ff;
        color: white;
    }
    #chatbot-block {
    margin:"30px";
    position: relative;
    padding: 2px; /* épaisseur de la bordure */
    border-radius: 10px;
    background: linear-gradient(
        45deg,
        rgb(229, 229, 229),
        rgb(31 41 55),
        rgb(229, 229, 229)
    );
    background-size: 200% 200%;
    animation: gradient-move 3s linear infinite;
    margin-bottom: 20px;
    }

    #chatbox {
        width: auto;
        height: 500px;
        overflow-y: auto;
        border-radius: 10px;
        background: rgba(11,15,23,1);
        padding: 15px;
    }
    @keyframes gradient-move { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
    .msg {
        padding: 8px 12px;
        border-radius: 6px;
        margin: 6px 0;
        max-width: 80%;
        line-height: 1.4;
    }
    .user {
        background: #0078ff;
        color: white;
        margin-left: auto;
        text-align: right;
    }
    .ai {
        background: #eaeaea;
        color: #333;
        margin-right: auto;
    }
    #inputArea,#searchFilter{
        display: flex;
        width: 95vw;
        max-width:800px;
        margin:auto;
        margin-top: 10px;

    }
    textarea {
        flex: 1;
        padding: 10px;
        border-radius: 6px;
        border: 2px solid transparent;
        font-family: sans-serif;
        font-size: 16px;
        margin-right: 10px !important;
        border: 2px solid  rgba(0,0,0,0.2);
        background-color: #dcdada;
    }
	textarea:focus {
	  outline: none;
	  border: 2px solid rgba(31,41,55,0.6);
	}
    #sendBtn {
        margin-left: 10px;
        padding: 10px 15px;
        border: none;
        background:  rgb(31 41 55);
        color: white;
        border-radius: 6px;
        cursor: pointer;
    }
    .loader {
        font-style: italic;
        opacity: 0.7;
        animation: blink 1s infinite;
    }
    @keyframes blink {
        0% { opacity: 0.7; }
        50% { opacity: 0.3; }
        100% { opacity: 0.7; }
    }
	

    /* */
 .upload-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  padding: 8px 14px;
  background-color: rgb(31 41 55);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  overflow: hidden;
}

.upload-btn, #sendBtn {
  transition: background 0.5s, transform 0.2s;
}
.upload-btn:hover , #sendBtn:hover {
  background-color: #0078ff;
  transform: translateY(-2px);
}

.upload-btn .icon {
  margin-right: 6px;
  font-size: 16px;
}

/* Cacher le vrai input */
.upload-btn .file-input {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}
</style>
