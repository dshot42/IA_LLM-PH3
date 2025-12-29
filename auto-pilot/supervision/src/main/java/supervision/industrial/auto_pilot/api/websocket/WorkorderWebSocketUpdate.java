package supervision.industrial.auto_pilot.api.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dependancy_bundle.model.Part;
import dependancy_bundle.model.Workorder;
import org.springframework.stereotype.Component;

/**
 * Replacement for Flask-SocketIO ws.py:
 * - keeps connected sessions
 * - allows server-side push of anomaly events to all clients
 */
@Component
public class WorkorderWebSocketUpdate extends SocketHandler {


    public void emitWorkorderCompleted(Workorder wo) {
        try {
            ObjectMapper mapper = new ObjectMapper();
            ObjectNode root = mapper.createObjectNode();
            root.put("event", "workorder");

            ObjectNode data = mapper.createObjectNode();
            data.put("workorder", mapper.writeValueAsString(wo));
            root.set("data", data);

            broadcastJson(root.toString());
        } catch (Exception ignored) {
        }
    }
}
