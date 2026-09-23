package com.generated;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@AutoConfigureMockMvc
class GeneratedApiTest {
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;
    JsonNode create(String path, String body) throws Exception {
        return json.readTree(mvc.perform(post(path).contentType("application/json").content(body))
            .andExpect(status().isCreated()).andReturn().getResponse().getContentAsString());
    }
    @Test void crudRelationsConstraintsAndComposition() throws Exception {
        JsonNode cliente = create("/api/cliente", "{\"nombre\":\"Ana\"}");
        long id = cliente.get("id").asLong();
        mvc.perform(post("/api/cliente").contentType("application/json").content("{\"nombre\":\"Ana\"}"))
            .andExpect(status().isConflict());
        mvc.perform(post("/api/pedido").contentType("application/json").content("{\"total\":5}"))
            .andExpect(status().isBadRequest());
        mvc.perform(post("/api/pedido").contentType("application/json").content("{\"total\":5,\"clienteId\":999999}"))
            .andExpect(status().isNotFound());
        JsonNode pedido = create("/api/pedido", "{\"total\":12.50,\"clienteId\":" + id + "}");
        long orderId = pedido.get("id").asLong();
        mvc.perform(get("/api/cliente/" + id + "/pedidos")).andExpect(status().isOk())
            .andExpect(jsonPath("$[0]").value(orderId));
        mvc.perform(get("/api/pedido/" + orderId)).andExpect(jsonPath("$.clienteId").value(id));
        String update = "{\"total\":25,\"clienteId\":" + id + ",\"entityVersion\":0}";
        mvc.perform(put("/api/pedido/" + orderId).contentType("application/json").content(update))
            .andExpect(status().isOk()).andExpect(jsonPath("$.total").value(25));
        mvc.perform(put("/api/pedido/" + orderId).contentType("application/json").content(update))
            .andExpect(status().isConflict());
        mvc.perform(get("/api/pedido?size=101")).andExpect(status().isBadRequest());
        mvc.perform(get("/api/pedido?page=0&size=1")).andExpect(status().isOk()).andExpect(jsonPath("$.length()").value(1));
        mvc.perform(delete("/api/cliente/" + id)).andExpect(status().isNoContent());
        mvc.perform(get("/api/pedido/" + orderId)).andExpect(status().isNotFound());
    }
    @Test void manyToManyAssignedKeysAndNoDeleteCascade() throws Exception {
        JsonNode tag = create("/api/etiqueta", "{}");
        long id = tag.get("id").asLong();
        create("/api/producto", "{\"codigo\":\"P1\",\"precio\":2.5,\"etiquetasIds\":[" + id + "]}");
        mvc.perform(get("/api/etiqueta/" + id + "/productos")).andExpect(status().isOk()).andExpect(jsonPath("$[0]").value("P1"));
        mvc.perform(put("/api/producto/P1").contentType("application/json").content("{\"codigo\":\"P2\",\"etiquetasIds\":[],\"entityVersion\":0}"))
            .andExpect(status().isBadRequest());
        mvc.perform(delete("/api/etiqueta/" + id)).andExpect(status().isConflict());
        mvc.perform(delete("/api/producto/P1")).andExpect(status().isNoContent());
        mvc.perform(get("/api/etiqueta/" + id)).andExpect(status().isOk());
    }
    @Test void oneToOneInheritanceAndTypes() throws Exception {
        JsonNode perfil = create("/api/perfil", "{}");
        create("/api/cliente", "{\"nombre\":\"Beto\",\"perfilId\":" + perfil.get("id") + "}");
        mvc.perform(post("/api/cliente").contentType("application/json").content("{\"nombre\":\"Carlos\",\"perfilId\":" + perfil.get("id") + "}"))
            .andExpect(status().isConflict());
        JsonNode empleado = create("/api/empleado", "{\"nombre\":\"Eva\",\"salario\":100}");
        assertEquals("Eva", empleado.get("nombre").asText());
        assertNotNull(empleado.get("id"));
        mvc.perform(get("/api/persona")).andExpect(status().isNotFound());
        JsonNode tipos = create("/api/tipos", "{\"numero\":2,\"largo\":12345678901,\"real\":1.5,\"activo\":true,\"fecha\":\"2026-09-14\",\"instante\":\"2026-09-14T12:30:00\",\"texto\":\"Texto libre\"}");
        assertEquals("2026-09-14", tipos.get("fecha").asText());
        assertTrue(tipos.get("activo").asBoolean());
    }
}
