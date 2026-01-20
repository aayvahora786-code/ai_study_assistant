from jinja2 import Environment, FileSystemLoader
import datetime

def generate_report(data):
    """
    Generate HTML report from exam analysis data using Jinja2 template.
    
    Args:
        data (dict): Contains exam_name, topic_freq, imp_questions, xp, streak, coins.
    
    Returns:
        str: Rendered HTML string.
    """
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("report_template.html")

    # Add date
    data["date"] = datetime.date.today().strftime("%d %B %Y")

    html_out = template.render(data=data)

    # Save to unique file per exam
    filename = f"report_{data['exam_name'].lower()}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_out)

    return html_out