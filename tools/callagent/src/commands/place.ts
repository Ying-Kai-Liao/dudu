export interface PlaceOptions {
  to: string;
  persona: string;
  goal: string;
  schema: string;
  tools?: string;
  context?: string;
  maxDuration: number;
  record: boolean;
  dryRun: boolean;
  output?: string;
  consentToken: string;
}

export async function placeCommand(_opts: PlaceOptions): Promise<void> {
  throw new Error("place not yet implemented");
}
