package com.skillbridge.app.core;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.ReactorClientHttpRequestFactory;
import org.springframework.web.client.RestClient;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;

import java.time.Duration;

/** Cung cap RestClient.Builder + WebClient.Builder (Boot 4 khong tu tao san trong cau hinh nay). */
@Configuration
public class AppConfig {

    @Bean
    public RestClient.Builder restClientBuilder() {
        // /scan-cv, /analyze... goi LLM ben Python core nen cham -> noi response timeout,
        // neu khong reactor netty timeout mac dinh se nem ReadTimeoutException.
        // ponytail: 3 phut du cho LLM; tang neu core cham hon.
        HttpClient httpClient = HttpClient.create().responseTimeout(Duration.ofMinutes(3));
        return RestClient.builder()
                .requestFactory(new ReactorClientHttpRequestFactory(httpClient));
    }

    /** Dung cho CoreClient.roadmapStream() (SSE, can WebClient reactive thay vi RestClient blocking). */
    @Bean
    public WebClient.Builder webClientBuilder() {
        return WebClient.builder();
    }
}
