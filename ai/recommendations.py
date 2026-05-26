def generate_recommendations(weak_topics):

    recommendations = []

    for topic in weak_topics:

        topic_lower = topic.lower()

        if "crm" in topic_lower:
            recommendations.append(
                "Повторить работу с CRM-системой"
            )

        elif "возврат" in topic_lower:
            recommendations.append(
                "Изучить модуль по возвратам"
            )

        elif "клиент" in topic_lower:
            recommendations.append(
                "Повторить правила общения с клиентами"
            )

        else:
            recommendations.append(
                f"Повторить тему: {topic}"
            )

    return list(set(recommendations))