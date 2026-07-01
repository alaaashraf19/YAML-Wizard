import { useEffect } from "react";
import gStyles from "../../global.module.css"
import styles from './Popup.module.css'
import { createPortal } from 'react-dom';

type PopupProps = {
    btnText1: string | null,
    btn1Action?: ((e: any) => void) | null,
    btnText2?: string | null,
    btn2Action?: ((e: any) => void) | null,
    questionMessage?: string | null,
    setQuestionMessage?: React.Dispatch<React.SetStateAction<string | null>> | null,
    confirmMessage?: string | null,
    setConfirmMessage?: React.Dispatch<React.SetStateAction<string | null>> | null,
    warningMessage?: string | null,
    setWarningMessage?: React.Dispatch<React.SetStateAction<string | null>> | null,
    errorMessage?: string | null,
    setErrorMessage?: React.Dispatch<React.SetStateAction<string | null>> | null,
    popupRef?: React.Ref<HTMLDivElement>
}

function Popup({
        btnText1,
        btn1Action,
        btnText2,
        btn2Action,
        questionMessage,
        setQuestionMessage,
        confirmMessage,
        setConfirmMessage,
        warningMessage,
        setWarningMessage,
        errorMessage,
        setErrorMessage,
        popupRef
    }:PopupProps){

    // Close popup on outside click
    useEffect(() => {
        function handleClickOutside(e: MouseEvent) {
            if((questionMessage || confirmMessage || errorMessage) && 
                popupRef && 
                'current' in popupRef &&
                popupRef.current &&
                !popupRef.current.contains(e.target as Node)){

                setQuestionMessage && setQuestionMessage("");
                setConfirmMessage && setConfirmMessage("");
                setErrorMessage && setErrorMessage("");
            }
        }

        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, [questionMessage, confirmMessage, errorMessage]);

    return createPortal(
        <div className={styles.popupLayover}>
            <div className={styles.popup} ref={popupRef}>
                {questionMessage && <p className={styles.questionMsg}>{questionMessage}</p>}
                {confirmMessage && <p className={styles.confirmMsg}>{confirmMessage}</p>}
                {warningMessage && <p className={styles.warningMsg}>{warningMessage}</p>}
                {errorMessage   && <p className={styles.errorMsg}>{errorMessage}</p>}

                <div className={styles.popupBtns}>
                    {btnText1 && 
                        <button className={`${styles.popupBtn} ${gStyles.gButton}`}
                            onClick={(e) => {
                                btn1Action && btn1Action(e);
                                setQuestionMessage && setQuestionMessage("");
                                setConfirmMessage && setConfirmMessage("");
                                setWarningMessage && setWarningMessage("");
                                setErrorMessage && setErrorMessage("");
                                }}>
                            {btnText1}
                        </button>
                    }
                    {btnText2 && questionMessage &&
                        <button className={`${styles.popupBtn} ${gStyles.gButton}`}
                            onClick={(e) => {
                                btn2Action && btn2Action(e);
                                setQuestionMessage && setQuestionMessage("");
                                setConfirmMessage && setConfirmMessage("");
                                setWarningMessage && setWarningMessage("");
                                setErrorMessage && setErrorMessage("");
                                }}>
                            {btnText2}
                        </button>
                    }
                </div>
            </div>
        </div>
    , document.body);
}

export default Popup;