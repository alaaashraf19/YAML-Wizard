import styles from "./ModelSwitch.module.css";

import type { Model } from "./../../pages/Chatbot";
import { useState, useEffect } from "react";

import { IoIosArrowDropdownCircle } from "react-icons/io";

const DEFAULT_MODELS: Model[] = [
    {
        id:"agent",
        label: "Main Model",
        available:true 
    },
    {
        id:"finetuned",
        label: "WIZARD Model"
    }
];


interface ModelSwitchProps {
    models: Model[];
    onModelChange: (model: Model) => void;
}

function ModelSwitch({ models = DEFAULT_MODELS, onModelChange }: ModelSwitchProps) {
    const [selectedIndex, setSelectedIndex] = useState<number>(0);
    const [isOpen, setIsOpen] = useState<boolean>(false);

    // Load saved model from sessionStorage on mount
    useEffect(() => {
        const savedModelLabel = sessionStorage.getItem("selected_model");
        if (savedModelLabel) {
            const index = models.findIndex(model => model.label === savedModelLabel);
            if (index !== -1) {
                setSelectedIndex(index);
            }
        }
    }, [models]);

    // Handle model selection
    const handleSelect = (index: number) => {
        const selectedModel = models[index];
        setSelectedIndex(index);
        sessionStorage.setItem("selected_model", selectedModel.label);
        setIsOpen(false);
        if (onModelChange) {
            onModelChange(selectedModel);
        }
    };

    // Toggle dropdown
    const toggleDropdown = () => {
        setIsOpen(prev => !prev);
    };

    return (
        <div className={styles.modelSwitchContainer}>
            <div className={styles.modelSelector} onClick={toggleDropdown}>
                <span className={styles.modelName}>{models[selectedIndex]?.label || "Select Model"}</span>
                <span className={`${styles.arrow} ${isOpen ? styles.arrowDown : styles.arrowUp}`}>
                    <IoIosArrowDropdownCircle/>
                </span>
            </div>
            {isOpen && (
                <div className={styles.dropdown}>
                    {models.length > 0 && models.map((model, index) => (
                        <div
                            key={index}
                            className={`${styles.dropdownItem} ${index === selectedIndex ? styles.active : ""}`}
                            onClick={() => handleSelect(index)}
                        >
                            {model.label}
                            {index === selectedIndex && <span className={styles.checkmark}>✓</span>}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default ModelSwitch;