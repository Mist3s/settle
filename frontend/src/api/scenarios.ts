/**
 * Scenarios API module.
 */

import client from "./client";
import type {
  ScenarioCreate,
  ScenarioUpdate,
  ScenarioResponse,
  ScenarioActionCreate,
  ScenarioActionUpdate,
  ScenarioActionResponse,
  ScenarioForecastResponse,
} from "@/types/api";

// -- Scenarios --------------------------------------------------------------

export async function getScenarios(params?: {
  status?: string;
}): Promise<ScenarioResponse[]> {
  const { data } = await client.get<ScenarioResponse[]>("/scenarios", {
    params,
  });
  return data;
}

export async function getScenario(id: string): Promise<ScenarioResponse> {
  const { data } = await client.get<ScenarioResponse>(`/scenarios/${id}`);
  return data;
}

export async function createScenario(
  scenario: ScenarioCreate,
): Promise<ScenarioResponse> {
  const { data } = await client.post<ScenarioResponse>("/scenarios", scenario);
  return data;
}

export async function updateScenario(
  id: string,
  update: ScenarioUpdate,
): Promise<ScenarioResponse> {
  const { data } = await client.patch<ScenarioResponse>(
    `/scenarios/${id}`,
    update,
  );
  return data;
}

export async function deleteScenario(id: string): Promise<void> {
  await client.delete(`/scenarios/${id}`);
}

// -- Scenario Actions -------------------------------------------------------

export async function getActions(
  scenarioId: string,
): Promise<ScenarioActionResponse[]> {
  const { data } = await client.get<ScenarioActionResponse[]>(
    `/scenarios/${scenarioId}/actions`,
  );
  return data;
}

export async function addAction(
  scenarioId: string,
  action: ScenarioActionCreate,
): Promise<ScenarioActionResponse> {
  const { data } = await client.post<ScenarioActionResponse>(
    `/scenarios/${scenarioId}/actions`,
    action,
  );
  return data;
}

export async function updateAction(
  scenarioId: string,
  actionId: string,
  update: ScenarioActionUpdate,
): Promise<ScenarioActionResponse> {
  const { data } = await client.patch<ScenarioActionResponse>(
    `/scenarios/${scenarioId}/actions/${actionId}`,
    update,
  );
  return data;
}

export async function deleteAction(
  scenarioId: string,
  actionId: string,
): Promise<void> {
  await client.delete(`/scenarios/${scenarioId}/actions/${actionId}`);
}

// -- Forecast & Apply -------------------------------------------------------

export async function getScenarioForecast(
  scenarioId: string,
  params: { from: string; to: string; starting_balance?: string },
): Promise<ScenarioForecastResponse> {
  const { data } = await client.get<ScenarioForecastResponse>(
    `/scenarios/${scenarioId}/forecast`,
    { params },
  );
  return data;
}

export async function applyScenario(scenarioId: string): Promise<void> {
  await client.post(`/scenarios/${scenarioId}/apply`);
}

export async function archiveScenario(scenarioId: string): Promise<void> {
  await client.post(`/scenarios/${scenarioId}/archive`);
}
