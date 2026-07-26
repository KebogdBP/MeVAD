import { useId } from "react";

interface SelectFieldProps {
  label: string;
  value: string;
  values: readonly string[];
  disabled?: boolean;
  hint?: string;
  error?: string;
  onChange: (value: string) => void;
}

export function SelectField({
  label,
  value,
  values,
  disabled = false,
  hint,
  error,
  onChange,
}: SelectFieldProps) {
  const id = useId();
  const messageId = hint || error ? `${id}-message` : undefined;

  return (
    <div className="ui-field field" data-invalid={Boolean(error) || undefined}>
      <label htmlFor={id}>{label}</label>
      <select
        id={id}
        value={value}
        disabled={disabled}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={messageId}
        onChange={(event) => onChange(event.target.value)}
      >
        {values.map((item) => (
          <option value={item} key={item}>
            {item.toUpperCase()}
          </option>
        ))}
      </select>
      {(error || hint) && (
        <small id={messageId} className="ui-field__message">
          {error ?? hint}
        </small>
      )}
    </div>
  );
}

interface NumberFieldProps {
  label: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  hint?: string;
  error?: string;
  onChange: (value: number) => void;
}

export function NumberField({
  label,
  value,
  min = 0,
  max,
  step = 0.1,
  hint,
  error,
  onChange,
}: NumberFieldProps) {
  const id = useId();
  const messageId = hint || error ? `${id}-message` : undefined;

  return (
    <div className="ui-field field" data-invalid={Boolean(error) || undefined}>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        aria-invalid={Boolean(error) || undefined}
        aria-describedby={messageId}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      {(error || hint) && (
        <small id={messageId} className="ui-field__message">
          {error ?? hint}
        </small>
      )}
    </div>
  );
}

interface CheckboxFieldProps {
  label: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (value: boolean) => void;
}

export function CheckboxField({
  label,
  checked,
  disabled = false,
  onChange,
}: CheckboxFieldProps) {
  const id = useId();

  return (
    <label className="ui-checkbox checkbox-field" htmlFor={id}>
      <input
        id={id}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span>{label}</span>
    </label>
  );
}
