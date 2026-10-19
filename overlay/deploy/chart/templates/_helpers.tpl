{{- define "fastapi.image" -}}
{{- $repository := required "Set image.repository to the tested artifact's repository" .Values.image.repository -}}
{{- if .Values.image.digest -}}
{{- printf "%s@%s" $repository .Values.image.digest -}}
{{- else if and .Values.localDevelopment .Values.image.tag (ne .Values.image.tag "latest") -}}
{{- printf "%s:%s" $repository .Values.image.tag -}}
{{- else -}}
{{- fail "Set image.digest; tag-only images are allowed only in explicit localDevelopment" -}}
{{- end -}}
{{- end -}}

{{- define "fastapi.labels" -}}
app.kubernetes.io/name: fastapi-service
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | quote }}
{{- end -}}

{{- define "fastapi.environment" -}}
{{- if .Values.database.enabled }}
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ required "database.secretName must reference an existing Secret" .Values.database.secretName | quote }}
      key: {{ .Values.database.secretKey | quote }}
{{- end }}
{{- range $name, $value := .Values.environment }}
{{- if eq $name "DATABASE_URL" }}{{ fail "Use database.secretName for DATABASE_URL" }}{{ end }}
- name: {{ $name | quote }}
  value: {{ $value | quote }}
{{- end }}
{{- end -}}

{{- define "fastapi.containerSecurity" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop: [ALL]
{{- end -}}

{{- define "fastapi.podSecurity" -}}
runAsNonRoot: true
runAsUser: 65532
runAsGroup: 65532
fsGroup: 65532
seccompProfile:
  type: RuntimeDefault
{{- end -}}
