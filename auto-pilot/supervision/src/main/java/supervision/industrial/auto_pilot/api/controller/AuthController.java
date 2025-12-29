package supervision.industrial.auto_pilot.api.controller;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.security.Key;
import java.util.Date;
import java.util.Map;

@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
public class AuthController {

    private static final String SECRET = "GJSF5K53DF8JNSL89SFJDHJDOJIFUJS34KNDIUH32437HSIDHFJSSFDSFSFDSFFDFFSDFJH FKJSG";

    private static Key getKey() {
        return Keys.hmacShaKeyFor(SECRET.getBytes(StandardCharsets.UTF_8));
    }

    public static String createToken(String username) {
        Date now = new Date();
        Date expiry = new Date(now.getTime() + 3600_000); // 1h

        return Jwts.builder()
                .subject(username)                // <= existe bien en 0.12.5
                .issuedAt(now)                    // <= issuedAt(Date)
                .expiration(expiry)               // <= expiration(Date)
                .signWith(getKey())               // <= HMAC-SHA selon la clé
                .compact();
    }

    public static String getSubject(String token) {
        return Jwts.parser()
                .verifyWith((SecretKey) getKey())
                .build()
                .parseSignedClaims(token)
                .getPayload()
                .getSubject();
    }

    @PostMapping("/login")
    public Map<String, String> login(@RequestBody LoginRequest req) {
        if (!"admin".equals(req.username()) || !"admin123".equals(req.password())) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED);
        }
        String token = createToken(req.username());
        return Map.of("access_token", token, "token_type", "Bearer");
    }

    public record LoginRequest(String username, String password) {}
}
