export type OpenApiDocument = {
  paths: Record<string, Record<string, OpenApiOperation>>;
  components?: {
    schemas?: Record<string, OpenApiSchema>;
    securitySchemes?: Record<string, unknown>;
  };
};

export type OpenApiOperation = {
  summary?: string;
  description?: string;
  tags?: string[];
  security?: unknown[];
  requestBody?: {
    required?: boolean;
    content?: Record<string, { schema?: OpenApiSchema }>;
  };
  responses?: Record<string, unknown>;
};

export type OpenApiSchema = {
  $ref?: string;
  type?: string;
  title?: string;
  properties?: Record<string, OpenApiSchema>;
  items?: OpenApiSchema;
  enum?: string[];
  required?: string[];
  default?: unknown;
  example?: unknown;
  anyOf?: OpenApiSchema[];
};

export async function fetchOpenApi(): Promise<OpenApiDocument> {
  const response = await fetch('/openapi.json');
  if (!response.ok) {
    throw new Error('Unable to load OpenAPI schema');
  }
  return response.json();
}

export function resolveSchema(
  schema: OpenApiSchema | undefined,
  doc: OpenApiDocument,
): OpenApiSchema | undefined {
  if (!schema) return undefined;
  if (schema.$ref) {
    const key = schema.$ref.split('/').pop() || '';
    return doc.components?.schemas?.[key];
  }
  if (schema.anyOf?.length) {
    return resolveSchema(schema.anyOf[0], doc);
  }
  return schema;
}

export function createExampleFromSchema(schema: OpenApiSchema | undefined, doc: OpenApiDocument): unknown {
  const resolved = resolveSchema(schema, doc);
  if (!resolved) return {};
  if (resolved.example !== undefined) return resolved.example;
  if (resolved.default !== undefined) return resolved.default;
  if (resolved.enum?.length) return resolved.enum[0];
  if (resolved.type === 'array') return [createExampleFromSchema(resolved.items, doc)];
  if (resolved.type === 'object' || resolved.properties) {
    return Object.fromEntries(
      Object.entries(resolved.properties || {}).map(([key, value]) => [key, createExampleFromSchema(value, doc)]),
    );
  }
  if (resolved.type === 'integer' || resolved.type === 'number') return 0;
  if (resolved.type === 'boolean') return false;
  return '';
}
