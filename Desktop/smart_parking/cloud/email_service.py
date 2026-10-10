# cloud/email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import EMAIL_SENDER, EMAIL_APP_PASSWORD


def _format_session_dates(entered_dt, exited_dt):
    """Build a human-friendly description of the parking session.
    Returns a tuple: (heading_line, entered_time_str, exited_time_str)

    If both timestamps fall on the same calendar day:
        heading = "Parking session: 26/04/2026"
        entered = "02:17"
        exited  = "02:22"

    If they span midnight, dates are shown inline next to each time:
        heading = "Parking session"
        entered = "25/04/2026 23:55"
        exited  = "26/04/2026 00:10"
    """
    same_day = entered_dt.date() == exited_dt.date()
    if same_day:
        heading = f"Parking session: {entered_dt.strftime('%d/%m/%Y')}"
        entered_str = entered_dt.strftime("%H:%M")
        exited_str = exited_dt.strftime("%H:%M")
    else:
        heading = "Parking session"
        entered_str = entered_dt.strftime("%d/%m/%Y %H:%M")
        exited_str = exited_dt.strftime("%d/%m/%Y %H:%M")
    return heading, entered_str, exited_str


def _format_real_duration(total_seconds):
    """Human-friendly description of the real parking time, e.g. '8m 27s'.
    Used in the disclaimer that explains why a session of 8:27 is billed
    as 9 minutes.
    """
    total_seconds = max(0, int(total_seconds))
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    if minutes == 0:
        return f"{seconds}s"
    return f"{minutes}m {seconds:02d}s"


class EmailService:
    def __init__(self):
        self.sender = EMAIL_SENDER
        self.password = EMAIL_APP_PASSWORD

    def _send(self, to_email, subject, body_html):
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender
            msg["To"] = to_email
            msg.attach(MIMEText(body_html, "html"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.sender, self.password)
                server.sendmail(self.sender, to_email, msg.as_string())
            print(f"[Email] Sent to {to_email}: {subject}")
            return True
        except Exception as e:
            print(f"[Email] Error: {e}")
            return False

    def send_exit_summary(self, to_email, first_name, duration_min, amount,
                          order_id, entered_dt, exited_dt):
        """Payment confirmation email sent after the user exits and pays.

        entered_dt, exited_dt: timezone-aware datetime objects.
        """
        # Order ID also appears in the subject so it shows up in the inbox
        # list, just like a real customer-service reference number.
        subject = f"Bar Parking - Payment Confirmation (Order {order_id})"

        heading, entered_str, exited_str = _format_session_dates(
            entered_dt, exited_dt
        )

        # Real elapsed time, used in the billing disclaimer below the table.
        real_seconds = (exited_dt - entered_dt).total_seconds()
        real_duration_str = _format_real_duration(real_seconds)

        body = f"""
        <html><body style="font-family: Arial, sans-serif; color: #222;">
        <h2 style="color: #2E5090; margin-bottom: 4px;">Bar Parking</h2>
        <p>Hello {first_name},</p>
        <p>Thank you for using Bar Parking! Here is your summary:</p>

        <p style="margin: 18px 0 6px 0; color: #555; font-size: 14px;">
            {heading}
        </p>

        <table style="border-collapse: collapse; margin: 4px 0 12px 0;
                      min-width: 320px;">
            <tr style="background: #f2f6fa;">
                <td style="padding: 10px 14px; border: 1px solid #ddd;"><b>Order ID</b></td>
                <td style="padding: 10px 14px; border: 1px solid #ddd;">{order_id}</td>
            </tr>
            <tr>
                <td style="padding: 10px 14px; border: 1px solid #ddd;"><b>Entered</b></td>
                <td style="padding: 10px 14px; border: 1px solid #ddd;">{entered_str}</td>
            </tr>
            <tr style="background: #f2f6fa;">
                <td style="padding: 10px 14px; border: 1px solid #ddd;"><b>Exited</b></td>
                <td style="padding: 10px 14px; border: 1px solid #ddd;">{exited_str}</td>
            </tr>
            <tr>
                <td style="padding: 10px 14px; border: 1px solid #ddd;"><b>Duration</b></td>
                <td style="padding: 10px 14px; border: 1px solid #ddd;">{duration_min} minutes</td>
            </tr>
            <tr style="background: #f2f6fa;">
                <td style="padding: 10px 14px; border: 1px solid #ddd;"><b>Amount Charged</b></td>
                <td style="padding: 10px 14px; border: 1px solid #ddd;">{amount} NIS</td>
            </tr>
            <tr>
                <td style="padding: 10px 14px; border: 1px solid #ddd;"><b>Payment</b></td>
                <td style="padding: 10px 14px; border: 1px solid #ddd;">Approved</td>
            </tr>
        </table>

        <p style="color: #666; font-size: 13px; margin: 0 0 20px 0;">
            Billing is per started minute. Your session: {real_duration_str}
            = {duration_min} billed minute{('s' if duration_min != 1 else '')}.
        </p>

        <p>Please keep this email for your records. If you have any questions,
           please reference your Order ID above.</p>
        <p>Have a nice day!</p>
        <p style="color: #888; font-size: 12px;">Bar Parking Smart System</p>
        </body></html>
        """
        return self._send(to_email, subject, body)

    def send_reservation_expired(self, to_email, first_name, order_id):
        """Cancellation/expiration email sent when a reservation expires
        without the user entering the parking lot.
        """
        subject = f"Bar Parking - Reservation Expired (Order {order_id})"
        body = f"""
        <html><body style="font-family: Arial, sans-serif; color: #222;">
        <h2 style="color: #2E5090; margin-bottom: 4px;">Bar Parking</h2>
        <p>Hello {first_name},</p>
        <p>Your parking reservation has expired because you did not arrive
           within 2 minutes.</p>

        <table style="border-collapse: collapse; margin: 4px 0 20px 0;
                      min-width: 320px;">
            <tr style="background: #f2f6fa;">
                <td style="padding: 10px 14px; border: 1px solid #ddd;"><b>Order ID</b></td>
                <td style="padding: 10px 14px; border: 1px solid #ddd;">{order_id}</td>
            </tr>
            <tr>
                <td style="padding: 10px 14px; border: 1px solid #ddd;"><b>Status</b></td>
                <td style="padding: 10px 14px; border: 1px solid #ddd;">Expired</td>
            </tr>
        </table>

        <p>Please make a new reservation on our website if you still need parking.</p>
        <p>If you have any questions, please reference your Order ID above.</p>
        <p>Have a nice day!</p>
        <p style="color: #888; font-size: 12px;">Bar Parking Smart System</p>
        </body></html>
        """
        return self._send(to_email, subject, body)