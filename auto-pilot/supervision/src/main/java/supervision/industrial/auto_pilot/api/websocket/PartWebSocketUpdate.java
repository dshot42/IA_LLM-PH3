package supervision.industrial.auto_pilot.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Replacement for Flask-SocketIO ws.py:
 * - keeps connected sessions
 * - allows server-side push of anomaly events to all clients
 */
@Component
public class PartWebSocketUpdate extends SocketHandler {


    public void emitPartCompleted() {
        try {
            ObjectMapper mapper = new ObjectMapper();
            ObjectNode root = mapper.createObjectNode();
            root.put("event", "part");

            ObjectNode data = mapper.createObjectNode();
            data.put("status", "completed");
            root.set("data", data);

            broadcastJson(root.toString());
        } catch (Exception ignored) {
        }
    }
}
