import { apiFetch } from './api';

export interface VersionInfo {
  sha: string;
  built_at: string;
  env: string;
}

export function getVersion() {
  return apiFetch<VersionInfo>('/version');
}
