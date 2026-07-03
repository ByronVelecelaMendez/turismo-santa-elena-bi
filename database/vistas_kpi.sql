-- ============================================================
-- KPI 1: Precio promedio de hospedaje por destino
-- Formula: SUM(precio_noche_usd) / COUNT(publicaciones_con_precio)
-- Fuentes reales: Booking + Airbnb + KAYAK + Hostelworld
-- ============================================================
CREATE OR REPLACE VIEW vw_kpi_precio_promedio_destino AS
SELECT 
    d.nombre_destino,
    d.tipo_destino,
    d.canton,
    COUNT(f.id_hecho) AS total_publicaciones,
    COUNT(f.precio_noche_usd) AS publicaciones_con_precio,
    ROUND(AVG(f.precio_noche_usd), 2) AS precio_promedio_noche_usd,
    MIN(f.precio_noche_usd) AS precio_minimo,
    MAX(f.precio_noche_usd) AS precio_maximo
FROM fact_hospedaje f
JOIN dim_destino d ON f.id_destino = d.id_destino
WHERE f.precio_noche_usd IS NOT NULL
GROUP BY d.nombre_destino, d.tipo_destino, d.canton
ORDER BY precio_promedio_noche_usd DESC;


-- ============================================================
-- KPI 2: Valoracion promedio por destino turistico
-- Formula: SUM(rating) / COUNT(resenas_por_destino)
-- Fuentes reales: Booking + Airbnb + KAYAK + Hostelworld
-- ============================================================
CREATE OR REPLACE VIEW vw_kpi_valoracion_promedio_destino AS
SELECT 
    d.nombre_destino,
    d.tipo_destino,
    COUNT(f.id_hecho) AS total_publicaciones,
    ROUND(AVG(f.rating), 2) AS valoracion_promedio,
    SUM(f.num_resenas) AS total_resenas,
    MIN(f.rating) AS valoracion_minima,
    MAX(f.rating) AS valoracion_maxima
FROM fact_hospedaje f
JOIN dim_destino d ON f.id_destino = d.id_destino
WHERE f.rating IS NOT NULL
GROUP BY d.nombre_destino, d.tipo_destino
ORDER BY valoracion_promedio DESC;


-- ============================================================
-- KPI 3: Indice de disponibilidad turistica
-- Formula: (publicaciones_con_precio / total_publicaciones) * 100
-- NOTA: el scraper no captura fechas disponibles individuales,
-- se aproxima como porcentaje de publicaciones con precio activo
-- (precio disponible = alojamiento disponible para reservar).
-- ============================================================
CREATE OR REPLACE VIEW vw_kpi_disponibilidad_turistica AS
SELECT 
    d.nombre_destino,
    p.nombre_plataforma,
    COUNT(f.id_hecho) AS total_publicaciones,
    COUNT(f.precio_noche_usd) AS publicaciones_con_precio,
    ROUND(
        (COUNT(f.precio_noche_usd)::decimal / COUNT(f.id_hecho)) * 100, 2
    ) AS indice_disponibilidad_pct
FROM fact_hospedaje f
JOIN dim_destino d ON f.id_destino = d.id_destino
JOIN dim_plataforma p ON f.id_plataforma = p.id_plataforma
GROUP BY d.nombre_destino, p.nombre_plataforma
ORDER BY d.nombre_destino, indice_disponibilidad_pct DESC;


-- ============================================================
-- KPI 4: Indice de demanda por temporada
-- Formula: (publicaciones_temporada / total_publicaciones) * 100
-- Fuentes: todas las plataformas + dim_temporada
-- NOTA: con datos actuales, el 100% es temporada baja (junio 2026).
-- Esta vista quedara enriquecida con futuras extracciones en
-- temporada alta/media.
-- ============================================================
CREATE OR REPLACE VIEW vw_kpi_demanda_por_temporada AS
SELECT 
    t.nombre_temporada,
    t.condicion_climatica,
    t.temperatura_promedio,
    COUNT(f.id_hecho) AS publicaciones_en_temporada,
    SUM(COUNT(f.id_hecho)) OVER () AS total_publicaciones_global,
    ROUND(
        (COUNT(f.id_hecho)::decimal / SUM(COUNT(f.id_hecho)) OVER ()) * 100, 2
    ) AS indice_demanda_pct,
    ROUND(AVG(f.precio_noche_usd), 2) AS precio_promedio_temporada
FROM fact_hospedaje f
JOIN dim_temporada t ON f.id_temporada = t.id_temporada
GROUP BY t.nombre_temporada, t.condicion_climatica, t.temperatura_promedio
ORDER BY indice_demanda_pct DESC;


-- ============================================================
-- KPI 5: Variacion de precios entre temporadas
-- Formula: ((precio_alta - precio_baja) / precio_baja) * 100
-- NOTA: con datos actuales solo existe temporada baja.
-- La vista calcula variacion entre temporadas disponibles;
-- quedara completa con extracciones futuras en otras temporadas.
-- ============================================================
CREATE OR REPLACE VIEW vw_kpi_variacion_precios_temporada AS
SELECT 
    d.nombre_destino,
    MAX(CASE WHEN t.nombre_temporada = 'alta' THEN f.precio_noche_usd END) AS precio_max_alta,
    MIN(CASE WHEN t.nombre_temporada = 'alta' THEN f.precio_noche_usd END) AS precio_min_alta,
    AVG(CASE WHEN t.nombre_temporada = 'alta' THEN f.precio_noche_usd END) AS precio_prom_alta,
    MAX(CASE WHEN t.nombre_temporada = 'baja' THEN f.precio_noche_usd END) AS precio_max_baja,
    MIN(CASE WHEN t.nombre_temporada = 'baja' THEN f.precio_noche_usd END) AS precio_min_baja,
    AVG(CASE WHEN t.nombre_temporada = 'baja' THEN f.precio_noche_usd END) AS precio_prom_baja,
    CASE 
        WHEN AVG(CASE WHEN t.nombre_temporada = 'alta' THEN f.precio_noche_usd END) IS NOT NULL
         AND AVG(CASE WHEN t.nombre_temporada = 'baja' THEN f.precio_noche_usd END) IS NOT NULL
        THEN ROUND(
            ((AVG(CASE WHEN t.nombre_temporada = 'alta' THEN f.precio_noche_usd END) - 
              AVG(CASE WHEN t.nombre_temporada = 'baja' THEN f.precio_noche_usd END)) /
              AVG(CASE WHEN t.nombre_temporada = 'baja' THEN f.precio_noche_usd END)) * 100, 2
        )
        ELSE NULL
    END AS variacion_alta_vs_baja_pct
FROM fact_hospedaje f
JOIN dim_destino d ON f.id_destino = d.id_destino
JOIN dim_temporada t ON f.id_temporada = t.id_temporada
WHERE f.precio_noche_usd IS NOT NULL
GROUP BY d.nombre_destino
ORDER BY d.nombre_destino;


-- ============================================================
-- KPI 6: Brecha entre expectativa (encuesta) y valoracion real
-- Formula: AVG(expectativa_encuesta) - AVG(rating_plataformas)
-- Este KPI cruza 2 fuentes: DW (rating real) y staging_encuesta
-- (satisfaccion percibida por el viajero).
-- Se implementa como vista sobre el DW + nota de complemento
-- con staging_encuesta para el dashboard.
-- ============================================================
CREATE OR REPLACE VIEW vw_kpi_valoracion_real_por_destino AS
SELECT 
    d.nombre_destino,
    ROUND(AVG(f.rating), 2) AS valoracion_real_plataformas,
    SUM(f.num_resenas) AS total_resenas,
    COUNT(f.id_hecho) AS publicaciones
FROM fact_hospedaje f
JOIN dim_destino d ON f.id_destino = d.id_destino
WHERE f.rating IS NOT NULL
GROUP BY d.nombre_destino
ORDER BY d.nombre_destino;
-- NOTA: la brecha completa (AVG_expectativa - AVG_rating_real) se
-- calcula en el dashboard cruzando esta vista con staging_encuesta.json,
-- ya que la encuesta no vive en el Star Schema (decision documentada en E3).


/*  BLOQUE DE CONSULTA A LAS VISTAS
SELECT * FROM vw_kpi_precio_promedio_destino;
SELECT * FROM vw_kpi_valoracion_promedio_destino;
SELECT * FROM vw_kpi_disponibilidad_turistica;
SELECT * FROM vw_kpi_demanda_por_temporada;
SELECT * FROM vw_kpi_variacion_precios_temporada;
SELECT * FROM vw_kpi_valoracion_real_por_destino;
*/