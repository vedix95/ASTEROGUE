# systems/shaders.py

LINE_VERTEX_SHADER = """
#version 330
in vec2 in_vert;
in vec3 in_color;

out vec3 v_color;

uniform vec2 u_camera;
uniform vec2 u_resolution;
uniform bool u_is_hud;
uniform float u_angle;
uniform float u_zoom;

void main() {
    vec2 pos;
    if (u_is_hud) {
        // Screen space coordinates (0 to width, 0 to height)
        // Convert to NDC (-1 to 1) with Y flipped (0 at top, height at bottom)
        pos.x = (in_vert.x / u_resolution.x) * 2.0 - 1.0;
        pos.y = 1.0 - (in_vert.y / u_resolution.y) * 2.0;
    } else {
        // World coordinates relative to camera center
        vec2 diff = in_vert - u_camera;
        
        // Rotate by u_angle around camera center
        float cos_a = cos(u_angle);
        float sin_a = sin(u_angle);
        vec2 rot_diff = vec2(
            diff.x * cos_a - diff.y * sin_a,
            diff.x * sin_a + diff.y * cos_a
        );
        
        pos = (rot_diff * u_zoom) / (u_resolution * 0.5);
        // Flip Y to match standard Cartesian coords in OpenGL
        pos.y = -pos.y;
    }
    gl_Position = vec4(pos, 0.0, 1.0);
    v_color = in_color;
}
"""

LINE_FRAGMENT_SHADER = """
#version 330
in vec3 v_color;
out vec4 fragColor;

void main() {
    fragColor = vec4(v_color, 1.0);
}
"""

POST_PROCESS_VERTEX_SHADER = """
#version 330
in vec2 in_vert;
out vec2 v_uv;

void main() {
    // Quad vertices are in [-1, 1], map to UV coordinates in [0, 1]
    v_uv = in_vert * 0.5 + 0.5;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

POST_PROCESS_FRAGMENT_SHADER = """
#version 330
uniform sampler2D u_texture;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_glitch;
uniform vec2 u_blackhole_pos;
uniform float u_blackhole_radius;
uniform float u_wave_intensity;
uniform vec4 u_menu_bounds; // left, bottom, right, top in UV space

in vec2 v_uv;
out vec4 fragColor;

void main() {
    vec2 uv = v_uv;
    
    // Menu wave distortion (vintage CRT behind)
    if (u_wave_intensity > 0.0) {
        // Only distort pixels outside the menu card bounding box
        if (uv.x < u_menu_bounds.x || uv.x > u_menu_bounds.z || uv.y < u_menu_bounds.y || uv.y > u_menu_bounds.w) {
            float wave = sin(uv.y * 11.0 + u_time * 3.8) * 0.007 * u_wave_intensity;
            uv.x += wave;
            float wave2 = cos(uv.x * 4.0 - u_time * 2.0) * 0.003 * u_wave_intensity;
            uv.y += wave2;
        }
    }
    
    // Black hole gravity bend/refraction (lensing)
    if (u_blackhole_radius > 0.0) {
        vec2 d = uv - u_blackhole_pos;
        float dist = length(d);
        if (dist > 0.0 && dist < u_blackhole_radius * 2.5) {
            float strength = 0.08 * (1.0 - (dist / (u_blackhole_radius * 2.5)));
            uv -= (d / dist) * strength;
        }
    }
    
    // Glitch horizontal line noise
    if (u_glitch > 0.0) {
        float noise = sin(uv.y * 100.0 + u_time * 20.0) * cos(uv.y * 20.0 - u_time * 10.0);
        if (abs(noise) > 0.45) {
            uv.x += noise * 0.018 * u_glitch;
        }
    }

    // Base scene texture
    vec4 base = texture(u_texture, uv);
    
    // RGB Split for Glitch
    if (u_glitch > 0.0) {
        vec4 base_r = texture(u_texture, uv + vec2(0.006 * u_glitch, 0.0));
        vec4 base_b = texture(u_texture, uv - vec2(0.006 * u_glitch, 0.0));
        base.r = base_r.r;
        base.b = base_b.b;
    }
    
    // Gaussian-like box blur to create bloom/neon-glow
    vec4 blur = vec4(0.0);
    float total_weight = 0.0;
    
    vec2 blur_step = vec2(2.5) / u_resolution;
    
    for (float x = -2.0; x <= 2.0; x += 1.0) {
        for (float y = -2.0; y <= 2.0; y += 1.0) {
            float dist = length(vec2(x, y));
            float weight = max(0.0, 1.0 - (dist / 3.0));
            if (weight > 0.0) {
                vec2 offset = vec2(x, y) * blur_step;
                blur += texture(u_texture, uv + offset) * weight;
                total_weight += weight;
            }
        }
    }
    blur = blur / total_weight;
    
    // Combine raw vectors and glow (scale glow by 1.25)
    vec3 color = base.rgb + blur.rgb * 1.25;
    
    // Add subtle scanlines (CRT television look)
    float scanline = 0.90 + 0.10 * sin(uv.y * u_resolution.y * 1.8 - u_time * 6.0);
    color *= scanline;
    
    // Subtle CRT Vignette (darken corners)
    vec2 uv_centered = uv - 0.5;
    float vignette = 1.0 - dot(uv_centered, uv_centered) * 0.45;
    color *= vignette;
    
    // Cathode-ray tube background glow (phosphor noise/residual charge)
    if (dot(color, color) < 0.005) {
        color = vec3(0.002, 0.012, 0.003); // vintage phosphor green glow
    }
    
    fragColor = vec4(color, 1.0);
}
"""
