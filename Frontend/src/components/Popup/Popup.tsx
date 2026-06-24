import { createPortal } from 'react-dom';
import styles from './Popup.module.css'

type PopupProps = {
    btnText1: string,
    btn1Action: ((e: any) => void) | null,
    btnText2: string | null,
    btn2Action: ((e: any) => void) | null,
    confirmMessage: string | null,
    setConfirmMessage: React.Dispatch<React.SetStateAction<string | null>> | null,
    warningMessage: string | null,
    setWarningMessage: React.Dispatch<React.SetStateAction<string | null>> | null,
    errorMessage: string | null,
    setErrorMessage: React.Dispatch<React.SetStateAction<string | null>> | null,
    popupRef: React.Ref<HTMLDivElement> | null
}

export function Popup({
        btnText1,
        btn1Action,
        btnText2,
        btn2Action,
        confirmMessage,
        setConfirmMessage,
        warningMessage,
        setWarningMessage,
        errorMessage,
        setErrorMessage,
        popupRef
    }:PopupProps){

    return createPortal(
        <div className={styles.popupLayover}>
            <div className={styles.popup} ref={popupRef}>
                {confirmMessage && <p className={styles.confirmMsg}>{confirmMessage}</p>}
                {warningMessage && <p className={styles.warningMsg}>{warningMessage}</p>}
                {errorMessage   && <p className={styles.errorMsg}>{errorMessage}</p>}

                <div className={styles.popupBtns}>
                    <button className={`${styles.popupBtn} ${styles.clickable}`}
                        onClick={(e) => {
                            btn1Action && btn1Action(e);
                            setConfirmMessage && setConfirmMessage("");
                            setWarningMessage && setWarningMessage("");
                            setErrorMessage && setErrorMessage("");
                            }}>
                        {btnText1}
                    </button>
                    {btnText2 &&
                        <button className={`${styles.popupBtn} ${styles.clickable}`}
                            onClick={(e) => {
                                btn2Action && btn2Action(e);
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