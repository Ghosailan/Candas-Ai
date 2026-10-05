import { useEffect, useMemo, useState } from 'react';
import { createExampleFromSchema, OpenApiDocument, OpenApiSchema, resolveSchema } from '../api/openapi';

type OpenApiFormProps = {
  doc: OpenApiDocument;
  schema?: OpenApiSchema;
  onChange: (value: unknown) => void;
};

function renderValue(value: unknown) {
  if (typeof value === 'string') return value;
  return JSON.stringify(value, null, 2);
}

export function OpenApiForm({ doc, schema, onChange }: OpenApiFormProps) {
  const resolved = useMemo(() => resolveSchema(schema, doc), [doc, schema]);
  const [text, setText] = useState('{}');

  useEffect(() => {
    const initial = createExampleFromSchema(resolved, doc);
    const serialized = JSON.stringify(initial, null, 2);
    setText(serialized);
    onChange(initial);
  }, [doc, onChange, resolved]);

  if (!resolved) {
    return <div className="api-form__empty">No request body</div>;
  }

  return (
    <div className="api-form">
      <div className="api-form__hint">
        {resolved.title || 'Generated body'} from OpenAPI schema
      </div>
      <textarea
        className="api-form__textarea"
        value={renderValue(text)}
        onChange={(event) => {
          const value = event.target.value;
          setText(value);
          try {
            onChange(JSON.parse(value));
          } catch {
            onChange(value);
          }
        }}
      />
    </div>
  );
}
