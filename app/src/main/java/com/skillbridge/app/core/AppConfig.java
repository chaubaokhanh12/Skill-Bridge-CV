package com.skillbridge.app.core;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;
import org.springframework.web.reactive.function.client.WebClient;

/** Cung cap RestClient.Builder + WebClient.Builder (Boot 4 khong tu tao san trong cau hinh nay). */
@Configuration
public class AppConfig {

    @Bean
    public RestClient.Builder restClientBuilder() {
        return RestClient.builder();
    }

    /** Dung cho CoreClient.roadmapStream() (SSE, can WebClient reactive thay vi RestClient blocking). */
    @Bean
    public WebClient.Builder webClientBuilder() {
        return WebClient.builder();
    }
}
