package supervision.industrial.auto_pilot.api.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import dependancy_bundle.model.PlcAnomaly;
import org.springframework.stereotype.Component;

/**
 * Replacement for Flask-SocketIO ws.py:
 * - keeps connected sessions
 * - allows server-side push of anomaly events to all clients
 */
@Component
public class AnomalyWebSocketHandler extends SocketHandler {


    public void emitAnomalieCompleted(PlcAnomaly plcAnomaly) {
        try {
            ObjectMapper mapper = new ObjectMapper();
            ObjectNode root = mapper.createObjectNode();
            root.put("event", "anomalie");

            ObjectNode data = mapper.createObjectNode();
            data.put("anomaly", mapper.writeValueAsString(plcAnomaly));

            root.set("data", data);

            broadcastJson(root.toString());
        } catch (Exception ignored) {
        }
    }
}
