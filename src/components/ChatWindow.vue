<template>
    <div class="chat-window" :style="{ height: windowHeight + 'px' }">
        <!-- Resize handle -->
        <div class="resize-handle resize-handle-bottom" @mousedown="startResize('bottom')"></div>
        <div class="chat-header">
            <h5><i class="fas fa-comments"></i> Chat</h5>
            <div class="session-info">
                <small>Session: {{ sessionId }}</small>
                <div class="connection-status">
                    <span :class="['status-indicator', connectionStatus]">
                        <i :class="getStatusIcon()"></i>
                        {{ getStatusText() }}
                    </span>
                </div>
            </div>
        </div>

        <div class="chat-messages" ref="messagesContainer">
            <div
                v-for="message in messages"
                :key="message.id"
                :class="['message', message.type]"
            >
                <div class="message-content">
                    <div class="message-text">{{ message.text }}</div>
                    <div class="message-time">{{ formatTime(message.timestamp) }}</div>
                </div>
            </div>
        </div>

        <div class="chat-input">
            <div class="input-group">
                <input
                    v-model="newMessage"
                    @keyup.enter="sendMessage"
                    type="text"
                    placeholder="Type your message..."
                    class="form-control"
                    :disabled="isLoading"
                />
                <div class="input-group-append">
                    <button
                        @click="sendMessage"
                        class="btn btn-primary"
                        :disabled="!newMessage.trim() || isLoading"
                    >
                        <i class="fas fa-paper-plane" v-if="!isLoading"></i>
                        <i class="fas fa-spinner fa-spin" v-else></i>
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import { store } from './Globals.js'

export default {
    name: 'ChatWindow',
    data () {
        return {
            messages: [],
            newMessage: '',
            isLoading: false,
            sessionId: this.generateSessionId(),
            messageId: 0,
            state: store,
            flightDataSent: false,
            connectionStatus: 'connecting', // connecting, connected, error
            // Resize functionality
            windowHeight: 500,
            isResizing: false,
            resizeType: null,
            startX: 0,
            startY: 0,
            startHeight: 0
        }
    },
    methods: {
        // Resize functionality
        startResize (type, event) {
            this.isResizing = true
            this.resizeType = type
            this.startX = event.clientX
            this.startY = event.clientY
            this.startHeight = this.windowHeight
            document.addEventListener('mousemove', this.handleResize)
            document.addEventListener('mouseup', this.stopResize)
            event.preventDefault()
        },

        handleResize (event) {
            if (!this.isResizing) return
            const deltaY = event.clientY - this.startY
            switch (this.resizeType) {
            case 'bottom':
                this.windowHeight = Math.max(200, this.startHeight + deltaY)
                break
            }
        },

        stopResize () {
            this.isResizing = false
            this.resizeType = null
            document.removeEventListener('mousemove', this.handleResize)
            document.removeEventListener('mouseup', this.stopResize)
        },

        generateSessionId () {
            // Generate a simple session ID based on timestamp
            return 'session_' + Date.now().toString(36)
        },

        formatTime (timestamp) {
            return new Date(timestamp).toLocaleTimeString()
        },

        async sendMessage () {
            if (!this.newMessage.trim() || this.isLoading) return

            const messageText = this.newMessage.trim()
            this.newMessage = ''

            // Add user message to chat
            this.addMessage(messageText, 'user')

            // Show loading state
            this.isLoading = true

            try {
                // Send message to backend API
                const response = await this.sendToAPI(messageText)

                // Add bot response to chat
                this.addMessage(response.message, 'bot')
            } catch (error) {
                console.error('Chat error:', error)
                this.addMessage(
                    'Sorry, there was an error processing your message. ' +
                    'Please check if the backend API is running.',
                    'bot'
                )
                this.connectionStatus = 'error'
            } finally {
                this.isLoading = false
            }
        },

        addMessage (text, type) {
            const message = {
                id: ++this.messageId,
                text: text,
                type: type,
                timestamp: Date.now()
            }

            this.messages.push(message)

            // Scroll to bottom
            this.$nextTick(() => {
                this.scrollToBottom()
            })
        },

        scrollToBottom () {
            const container = this.$refs.messagesContainer
            if (container) {
                container.scrollTop = container.scrollHeight
            }
        },

        async sendToAPI (message) {
            // API endpoint for the Flask backend
            const API_BASE_URL = 'http://localhost:8000/api'

            const response = await fetch(`${API_BASE_URL}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': this.sessionId
                },
                body: JSON.stringify({
                    message: message,
                    sessionId: this.sessionId,
                    timestamp: Date.now()
                })
            })

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`)
            }

            return await response.json()
        },

        async sendFlightDataToBackend () {
            if (this.flightDataSent || !this.state.processDone) return

            try {
                // Prepare flight data from the global state (send all relevant data fields)
                const flightData = {
                    // Core
                    vehicle: this.state.vehicle,
                    logType: this.state.logType,
                    file: this.state.file,
                    metadata: this.state.metadata,
                    params: this.state.params,
                    defaultParams: this.state.defaultParams,
                    // Trajectories and attitude
                    trajectories: this.state.trajectories,
                    timeTrajectory: this.state.timeTrajectory,
                    timeAttitude: this.state.timeAttitude,
                    timeAttitudeQ: this.state.timeAttitudeQ,
                    trajectorySource: this.state.trajectorySource,
                    trajectorySources: this.state.trajectorySources,
                    attitudeSources: this.state.attitudeSources,
                    attitudeSource: this.state.attitudeSource,
                    // Mission and events
                    mission: this.state.mission,
                    flightModeChanges: this.state.flightModeChanges,
                    events: this.state.events,
                    fences: this.state.fences,
                    // Additional time/context
                    currentTime: this.state.currentTime,
                    timeRange: this.state.timeRange,
                    // Derived/text data
                    textMessages: this.state.textMessages,
                    namedFloats: this.state.namedFloats,
                    // Caching and misc
                    plotCache: this.state.plotCache,
                    commit: this.state.commit,
                    buildDate: this.state.buildDate,
                    // Processing status (useful context)
                    processStatus: this.state.processStatus,
                    processPercentage: this.state.processPercentage
                }

                const API_BASE_URL = 'http://localhost:8000/api'

                const response = await fetch(`${API_BASE_URL}/flight-data`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Session-ID': this.sessionId
                    },
                    body: JSON.stringify(flightData)
                })

                if (response.ok) {
                    const result = await response.json()
                    console.log('Flight data sent to backend:', result)
                    this.flightDataSent = true
                    this.connectionStatus = 'connected'

                    // Add a message about the flight data being loaded
                    this.addMessage(
                        `Flight data loaded! I can see ${result.available_data_types.length} ` +
                        'types of data available. Ask me about your flight!',
                        'bot'
                    )
                } else {
                    console.error('Failed to send flight data:', response.status)
                    this.connectionStatus = 'error'
                }
            } catch (error) {
                console.error('Error sending flight data:', error)
                this.connectionStatus = 'error'
            }
        },

        async checkBackendConnection () {
            try {
                const response = await fetch('http://localhost:8000/api/health')
                if (response.ok) {
                    this.connectionStatus = 'connected'
                    return true
                } else {
                    this.connectionStatus = 'error'
                    return false
                }
            } catch (error) {
                console.error('Backend connection error:', error)
                this.connectionStatus = 'error'
                return false
            }
        },

        getStatusIcon () {
            switch (this.connectionStatus) {
            case 'connected':
                return 'fas fa-check-circle'
            case 'error':
                return 'fas fa-exclamation-triangle'
            case 'connecting':
            default:
                return 'fas fa-spinner fa-spin'
            }
        },

        getStatusText () {
            switch (this.connectionStatus) {
            case 'connected':
                return 'Connected'
            case 'error':
                return 'Connection Error'
            case 'connecting':
            default:
                return 'Connecting...'
            }
        }
    },

    async mounted () {
        // Check backend connection
        const isConnected = await this.checkBackendConnection()

        if (isConnected) {
            this.addMessage(
                'Welcome to UAV Log Viewer Chat! I\'m connected and ready to help you analyze your flight data.',
                'bot'
            )
        } else {
            this.addMessage(
                'Welcome to UAV Log Viewer Chat! I\'m having trouble connecting to the backend API. ' +
                'Please make sure it\'s running on port 8000.',
                'bot'
            )
        }

        // Send flight data if already processed
        if (this.state.processDone) {
            await this.sendFlightDataToBackend()
        }
    },

    watch: {
        // Watch for when flight data is processed
        'state.processDone' (newValue) {
            if (newValue && !this.flightDataSent) {
                this.sendFlightDataToBackend()
            }
        }
    },

    beforeDestroy () {
        // Clean up event listeners
        document.removeEventListener('mousemove', this.handleResize)
        document.removeEventListener('mouseup', this.stopResize)
    }
}
</script>

<style scoped>
.chat-window {
  display: flex;
  flex-direction: column;
  background: linear-gradient(0deg, rgb(20, 25, 36) 51%, rgb(37, 47, 71) 100%);
  overflow: hidden;
  position: relative;
  min-height: 200px;
  height: 100%;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  border-left: 3px solid #2e353d;
}

.chat-header {
  background-color: rgba(29, 36, 52, 0.8);
  padding: 12px 16px;
  border-bottom: 1px solid #23282e;
  color: #ffffff;
}

.chat-header h5 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: rgb(54, 72, 114);
}

.chat-header h5 i {
  margin-right: 8px;
  color: rgb(54, 72, 114);
}

.session-info {
  margin-top: 4px;
}

.session-info small {
    color: rgb(146, 143, 143);
    font-size: 11px;
}

.connection-status {
    margin-top: 4px;
}

.status-indicator {
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 3px;
    display: inline-flex;
    align-items: center;
    gap: 4px;
}

.status-indicator.connected {
    background-color: rgba(76, 175, 80, 0.2);
    color: #4caf50;
}

.status-indicator.error {
    background-color: rgba(244, 67, 54, 0.2);
    color: #f44336;
}

.status-indicator.connecting {
    background-color: rgba(255, 193, 7, 0.2);
    color: #ffc107;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  background: linear-gradient(0deg, rgb(20, 25, 36) 51%, rgb(37, 47, 71) 100%);
}

.message {
  margin-bottom: 12px;
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message.bot {
  justify-content: flex-start;
}

.message-content {
  max-width: 80%;
  padding: 8px 12px;
  border-radius: 12px;
  position: relative;
}

.message.user .message-content {
  background-color: rgba(52, 70, 100, 0.8);
  color: #ffffff;
  border-bottom-right-radius: 4px;
  border-left: 3px solid #01204191;
}

.message.bot .message-content {
  background-color: rgba(47, 60, 83, 0.63);
  color: #ffffff;
  border-bottom-left-radius: 4px;
  border-left: 3px solid #2e353d;
}

.message.user .message-content:hover {
  background-color: rgba(52, 70, 100, 0.9);
  box-shadow: 0px 0px 12px 0px rgba(24, 106, 173, 0.281);
}

.message.bot .message-content:hover {
  background-color: rgba(58, 71, 94, 0.63);
  box-shadow: 0px 0px 12px 0px rgba(24, 106, 173, 0.281);
}

.message-text {
  font-size: 14px;
  line-height: 1.4;
  word-wrap: break-word;
}

.message-time {
  font-size: 11px;
  opacity: 0.7;
  margin-top: 4px;
  color: rgb(146, 143, 143);
}

.chat-input {
  padding: 12px;
  background-color: rgba(29, 36, 52, 0.8);
  border-top: 1px solid #23282e;
}

.input-group {
  display: flex;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}

.form-control {
  background-color: rgba(47, 60, 83, 0.63);
  border: 1px solid #23282e;
  color: #ffffff;
  border-radius: 6px 0 0 6px;
  padding: 8px 12px;
  font-size: 14px;
  flex: 1;
  min-width: 0;
  box-sizing: border-box;
}

.form-control:focus {
  background-color: rgba(47, 60, 83, 0.8);
  border-color: rgb(54, 72, 114);
  color: #ffffff;
  box-shadow: 0 0 0 0.2rem rgba(54, 72, 114, 0.25);
}

.form-control::placeholder {
  color: rgb(146, 143, 143);
}

.btn {
  border-radius: 0 6px 6px 0;
  padding: 8px 12px;
  border: 1px solid rgb(54, 72, 114);
  background-color: rgb(54, 72, 114);
  color: #ffffff;
  font-size: 14px;
  transition: all 0.2s ease;
  flex-shrink: 0;
  white-space: nowrap;
}

.btn:hover:not(:disabled) {
  background-color: rgba(54, 72, 114, 0.8);
  border-color: rgba(54, 72, 114, 0.8);
  box-shadow: 0px 0px 12px 0px rgba(54, 72, 114, 0.5);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Scrollbar styling - match sidebar */
.chat-messages::-webkit-scrollbar {
  width: 12px;
  background-color: rgba(0, 0, 0, 0);
}

.chat-messages::-webkit-scrollbar-thumb {
  border-radius: 5px;
  box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.1);
  background: rgb(60, 75, 112);
  background: linear-gradient(0deg, rgb(67, 95, 155) 51%, rgb(61, 79, 121) 100%);
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(0deg, rgb(77, 105, 165) 51%, rgb(71, 89, 131) 100%);
}

/* Resize handle */
.resize-handle {
  position: absolute;
  background-color: transparent;
  z-index: 10;
}

.resize-handle-bottom {
  bottom: 0;
  left: 0;
  width: 100%;
  height: 4px;
  cursor: ns-resize;
}

/* Show resize cursor on hover */
.chat-window:hover .resize-handle-bottom {
  background-color: rgba(54, 72, 114, 0.3);
}
</style>
