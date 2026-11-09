/**
 * Point d'entrée des 18 services d'IA de doc 16 §9.3 (baseline v1). Chaque module expose une fonction
 * pure (fetchX, testable avec un client explicite) et un hook React Query qui l'appelle.
 */
export * from "./client";
export * from "./keys";
export * from "./weather"; //                 1
export * from "./soil-forecast"; //           2
export * from "./irrigation-need"; //         3
export * from "./irrigation-plan"; //         4
export * from "./recommendations"; //         5
export * from "./fertilization"; //           6
export * from "./kit-parameters"; //          7
export * from "./disease-diagnosis"; //       8
export * from "./pest-risk"; //               9
export * from "./trap-counts"; //            10
export * from "./vegetation"; //             11
export * from "./yield-forecast"; //         12
export * from "./device-health"; //          13
export * from "./water-savings"; //          14
export * from "./price-forecast"; //         15
export * from "./assistant-chat"; //         16
export * from "./assistant-transcribe"; //   17
export * from "./map-layers"; //             18
