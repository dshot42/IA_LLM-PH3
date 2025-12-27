package supervision.industrial.auto_pilot.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.stereotype.Component;

/**
 * Replacement for Flask-SocketIO ws.py:
 * - keeps connected sessions
 * - allows server-side push of anomaly events to all clients
 */
@Component
public class AnomalyWebSocketHandler extends SocketHandler {


    public void emitAnomalieCompleted() {
        try {
            ObjectMapper mapper = new ObjectMapper();
            ObjectNode root = mapper.createObjectNode();
            root.put("event", "anomalie");

            ObjectNode data = mapper.createObjectNode();
            data.put("status", "completed");

            root.set("data", data);

            broadcastJson(root.toString());
        } catch (Exception ignored) {
        }
    }
}
