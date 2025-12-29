package supervision.industrial.auto_pilot.api.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dependancy_bundle.model.Part;
import org.springframework.stereotype.Component;

/**
 * Replacement for Flask-SocketIO ws.py:
 * - keeps connected sessions
 * - allows server-side push of anomaly events to all clients
 */
@Component
public class PartWebSocketUpdate extends SocketHandler {


    public void emitPartCompleted(Part p) {
        try {
            ObjectMapper mapper = new ObjectMapper();
            ObjectNode root = mapper.createObjectNode();
            root.put("event", "part");

            ObjectNode data = mapper.createObjectNode();
            data.put("part", mapper.writeValueAsString(p));
            root.set("data", data);

            broadcastJson(root.toString());
        } catch (Exception ignored) {
        }
    }
}
