import styles from './UserProfile.module.css'

function UserProfile() {
    return(<>
        <div className={styles.formContainer}>
            <p className={styles.header}>Profile</p>
            <form className={styles.section}>
                <p>Information</p>
                <label id='name'>
                    Name: 
                    <input type="text" />
                </label>
            </form>
        </div>
    </>)
}

export default UserProfile;