# Diematic to MQTT (module HACS)

Ce dépôt adapte le projet [Benoit3/Diematic_to_MQTT](https://github.com/Benoit3/Diematic_to_MQTT) sous forme d'intégration **Home Assistant** installable via **HACS**.

## Ce que fait l'intégration

- Lance un bridge entre un convertisseur Modbus/TCP (RS485) et MQTT.
- Réutilise la logique Diematic3 / Diematic4 / Diematic Delta du projet d'origine.
- Publie les états de la chaudière dans MQTT.
- Gère les commandes MQTT (`.../set`) pour modifier les consignes.
- Envoie les messages MQTT Discovery Home Assistant (optionnel).

## Installation via HACS (custom repository)

1. HACS → `Integrations` → menu ⋮ → `Custom repositories`.
2. Ajouter l'URL `https://github.com/kromagnsss/DTMQTT` avec le type `Integration`.
3. Installer **Diematic to MQTT**.
4. Redémarrer Home Assistant.
5. Aller dans `Paramètres` → `Appareils et services` → `Ajouter une intégration` → `Diematic to MQTT`.

## Paramètres de configuration

Pendant le flow de configuration, renseigner :

- `modbus_host` / `modbus_port` : IP/port du convertisseur RS485↔TCP.
- `regulator_type` : `Diematic3`, `Diematic4` ou `DiematicDelta`.
- `regulator_address` : adresse Modbus du régulateur.
- `interface_address` : adresse Modbus de l'interface (Delta).
- `period` : période de rafraîchissement.
- Paramètres MQTT (`mqtt_host`, `mqtt_port`, `mqtt_client_id`, etc.).
- `discovery_enabled` + `discovery_prefix` pour publication MQTT Discovery.

## Arborescence HACS

- `hacs.json`
- `custom_components/diematic_to_mqtt/*`

## Crédits

- Basé sur le projet original de Benoit3 :
  https://github.com/Benoit3/Diematic_to_MQTT
