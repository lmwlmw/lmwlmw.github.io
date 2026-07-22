---
title: "Stats"
layout: single
permalink: /stats/
author_profile: false
comments: false
toc: false
---

방문 통계 페이지입니다.

{% if site.goatcounter.public_dashboard_url %}
<div class="stats-embed">
  <iframe
    src="{% if site.goatcounter.public_dashboard_url contains '?' %}{{ site.goatcounter.public_dashboard_url }}&hideui=1{% else %}{{ site.goatcounter.public_dashboard_url }}?hideui=1{% endif %}"
    title="Site analytics dashboard"
    loading="lazy"></iframe>
</div>
{% else %}
아직 통계 대시보드 주소가 설정되지 않았습니다.

설정이 끝나면 이 페이지에 GoatCounter 대시보드가 바로 표시됩니다.
{% endif %}
