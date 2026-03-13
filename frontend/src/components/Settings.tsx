import { useEffect, useState } from "react";

interface Props {
  weight: number;
  onWeightChange: (weight: number) => void;
}

export function Settings({ weight, onWeightChange }: Props) {
  const [inputValue, setInputValue] = useState(weight.toString());
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    setInputValue(weight.toString());
  }, [weight]);

  const handleSave = () => {
    const parsed = parseFloat(inputValue);
    if (!isNaN(parsed) && parsed > 0) {
      onWeightChange(parsed);
    }
  };

  return (
    <section className="settings">
      <button className="settings-toggle" onClick={() => setIsOpen(!isOpen)}>
        <span>Settings</span>
        <span className="toggle-icon">{isOpen ? "▲" : "▼"}</span>
      </button>
      {isOpen && (
        <div className="settings-body">
          <div className="settings-row">
            <label>
              Weight (kg)
              <div className="weight-input-group">
                <input
                  type="number"
                  min="1"
                  step="0.1"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                />
                <button onClick={handleSave}>Save</button>
              </div>
            </label>
          </div>
        </div>
      )}
    </section>
  );
}
